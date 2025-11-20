#!/usr/bin/env python
"""Check and update pending transactions"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import TopUpIntent, OnChainTransaction
from wallet.blockchain import BlockchainMonitor

# Get pending transactions
pending_txs = OnChainTransaction.objects.filter(status='pending').select_related('network', 'user', 'topup_intent')
print('Checking pending transactions...\n')

for tx in pending_txs:
    print(f'Transaction: {tx.tx_hash[:50]}...')
    print(f'  User: {tx.user.email}')
    print(f'  Amount: ${tx.amount_minor/100:.2f}')
    print(f'  Confirmations: {tx.confirmations}/{tx.required_confirmations}')
    print(f'  Network: {tx.network.name}')
    
    # Check if we can verify it
    if tx.topup_intent:
        print(f'  TopUp Intent: {tx.topup_intent.id} ({tx.topup_intent.status})')
        monitor = BlockchainMonitor(tx.network)
        try:
            found = monitor.check_deposit_address(tx.topup_intent.deposit_address, tx.topup_intent)
            tx.refresh_from_db()
            print(f'  Status after check: {tx.status} ({tx.confirmations}/{tx.required_confirmations} conf)')
            if tx.status == 'confirmed':
                print(f'  ✅ Transaction confirmed!')
        except Exception as e:
            print(f'  ❌ Error checking: {e}')
    print()

# Also check expired pending top-ups
print('\n' + '=' * 80)
print('Checking expired pending top-ups...\n')
from django.utils import timezone
expired_pending = TopUpIntent.objects.filter(status='pending', expires_at__lt=timezone.now())
print(f'Found {expired_pending.count()} expired top-ups still marked as pending')
if expired_pending.exists():
    print('Updating to expired status...')
    expired_pending.update(status='expired')
    print('✅ Updated!')

