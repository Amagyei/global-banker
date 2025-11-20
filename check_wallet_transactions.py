#!/usr/bin/env python
"""Check wallet transaction status"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import TopUpIntent, OnChainTransaction, Wallet, DepositAddress
from django.utils import timezone
from collections import defaultdict

print('=' * 80)
print('WALLET TRANSACTION STATUS REPORT')
print('=' * 80)

# TopUp Intent Statuses
print('\n📊 TOP-UP INTENTS BY STATUS:')
print('-' * 80)
intents_by_status = defaultdict(list)
for intent in TopUpIntent.objects.all().select_related('user', 'network', 'deposit_address').order_by('-created_at'):
    intents_by_status[intent.status].append(intent)

for status, intents in sorted(intents_by_status.items()):
    print(f'\n{status.upper()}: {len(intents)} intents')
    for intent in intents[:5]:  # Show first 5
        expired = ' (EXPIRED)' if intent.is_expired() else ''
        addr = intent.deposit_address.address[:30] if intent.deposit_address else "N/A"
        print(f'  • {intent.user.email[:30]:30} | ${intent.amount_minor/100:8.2f} | {intent.network.name:10} | {addr:30}{expired}')
    if len(intents) > 5:
        print(f'  ... and {len(intents) - 5} more')

# OnChain Transactions
print('\n\n🔗 ON-CHAIN TRANSACTIONS BY STATUS:')
print('-' * 80)
txs_by_status = defaultdict(list)
for tx in OnChainTransaction.objects.all().select_related('user', 'network', 'topup_intent').order_by('-occurred_at'):
    txs_by_status[tx.status].append(tx)

for status, txs in sorted(txs_by_status.items()):
    print(f'\n{status.upper()}: {len(txs)} transactions')
    for tx in txs[:5]:  # Show first 5
        print(f'  • {tx.user.email[:30]:30} | {tx.network.name:10} | ${tx.amount_minor/100:8.2f} USD | {tx.confirmations}/{tx.required_confirmations} conf | {tx.tx_hash[:30]}...')
    if len(txs) > 5:
        print(f'  ... and {len(txs) - 5} more')

# Recent Activity
print('\n\n⏰ RECENT TOP-UP ACTIVITY (Last 10):')
print('-' * 80)
recent = TopUpIntent.objects.all().select_related('user', 'network').order_by('-created_at')[:10]
for intent in recent:
    expired = ' ⚠️ EXPIRED' if intent.is_expired() else ''
    print(f'{intent.created_at.strftime("%Y-%m-%d %H:%M:%S"):20} | {intent.user.email[:25]:25} | {intent.status:20} | ${intent.amount_minor/100:8.2f}{expired}')

# Wallet Balances
print('\n\n💰 WALLET BALANCES:')
print('-' * 80)
wallets = Wallet.objects.all().select_related('user').order_by('-balance_minor')
print(f'Total wallets: {wallets.count()}')
for wallet in wallets[:10]:
    print(f'  • {wallet.user.email[:40]:40} | ${wallet.balance_minor/100:10.2f} | Pending: ${wallet.pending_minor/100:8.2f}')

# Pending/Failed Summary
print('\n\n⚠️  ISSUES SUMMARY:')
print('-' * 80)
pending = TopUpIntent.objects.filter(status='pending')
expired = TopUpIntent.objects.filter(status='expired')
failed = TopUpIntent.objects.filter(status='failed')
awaiting = TopUpIntent.objects.filter(status='awaiting_confirmations')

print(f'Pending top-ups: {pending.count()}')
print(f'Expired top-ups: {expired.count()}')
print(f'Failed top-ups: {failed.count()}')
print(f'Awaiting confirmations: {awaiting.count()}')

if pending.exists():
    print('\nPending top-ups (may need monitoring):')
    for intent in pending[:5]:
        print(f'  • {intent.user.email} | ${intent.amount_minor/100:.2f} | Created: {intent.created_at.strftime("%Y-%m-%d %H:%M")}')

# Deposit Addresses with pending top-ups
print('\n\n📍 ACTIVE DEPOSIT ADDRESSES WITH PENDING TOP-UPS:')
print('-' * 80)
active_addresses = DepositAddress.objects.filter(
    is_active=True,
    topup_intents__status__in=['pending', 'awaiting_confirmations']
).distinct().select_related('user', 'network')

if active_addresses.exists():
    for addr in active_addresses[:10]:
        pending_intents = addr.topup_intents.filter(status__in=['pending', 'awaiting_confirmations'])
        print(f'  • {addr.address[:50]:50} | {addr.user.email[:25]:25} | {addr.network.name:10} | {pending_intents.count()} pending')
else:
    print('  No active addresses with pending top-ups')

print('\n' + '=' * 80)

