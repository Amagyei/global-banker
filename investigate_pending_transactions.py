#!/usr/bin/env python
"""Investigate why transactions are stuck pending"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import TopUpIntent, OnChainTransaction, DepositAddress
from wallet.blockchain import BlockchainMonitor
from django.utils import timezone
from datetime import timedelta

print('=' * 80)
print('INVESTIGATING PENDING TRANSACTIONS')
print('=' * 80)

# Get pending transactions
pending_txs = OnChainTransaction.objects.filter(status='pending').select_related('network', 'user', 'topup_intent', 'topup_intent__deposit_address')
print(f'\nFound {pending_txs.count()} pending transactions\n')

for tx in pending_txs:
    print(f'Transaction: {tx.tx_hash}')
    print(f'  User: {tx.user.email}')
    print(f'  Amount: ${tx.amount_minor/100:.2f}')
    print(f'  Confirmations: {tx.confirmations}/{tx.required_confirmations}')
    print(f'  Created: {tx.created_at}')
    print(f'  Age: {(timezone.now() - tx.created_at).total_seconds() / 3600:.1f} hours')
    
    # Check if transaction exists on blockchain
    monitor = BlockchainMonitor(tx.network)
    print(f'\n  Checking blockchain status...')
    
    try:
        # Try to get transaction from blockchain
        blockchain_tx = monitor.get_transaction(tx.tx_hash)
        if blockchain_tx:
            print(f'  ✅ Transaction found on blockchain')
            print(f'  Status: {blockchain_tx.get("status", "unknown")}')
            if 'confirmations' in blockchain_tx:
                print(f'  Confirmations on chain: {blockchain_tx["confirmations"]}')
            if 'block_height' in blockchain_tx:
                print(f'  Block height: {blockchain_tx["block_height"]}')
        else:
            print(f'  ❌ Transaction NOT found on blockchain')
            print(f'  This transaction may not have been broadcast or may be invalid')
    except Exception as e:
        print(f'  ❌ Error checking blockchain: {e}')
    
    # Check deposit address
    if tx.topup_intent and tx.topup_intent.deposit_address:
        deposit_addr = tx.topup_intent.deposit_address
        print(f'\n  Checking deposit address: {deposit_addr.address}')
        try:
            # Get all transactions for this address
            addr_txs = monitor.get_address_transactions(deposit_addr.address)
            print(f'  Found {len(addr_txs)} transactions for this address')
            
            # Check if our transaction is in the list
            our_tx_found = False
            for addr_tx in addr_txs[:5]:  # Check first 5
                if addr_tx.get('txid') == tx.tx_hash:
                    our_tx_found = True
                    print(f'  ✅ Our transaction found in address history')
                    print(f'  Status: {addr_tx.get("status", {}).get("confirmed", False)}')
                    if addr_tx.get('status', {}).get('block_height'):
                        print(f'  Block height: {addr_tx["status"]["block_height"]}')
                    break
            
            if not our_tx_found:
                print(f'  ⚠️  Our transaction NOT in address history')
                print(f'  This suggests the transaction may not have been sent to this address')
        except Exception as e:
            print(f'  ❌ Error checking address: {e}')
    
    # Check top-up intent
    if tx.topup_intent:
        print(f'\n  TopUp Intent Status: {tx.topup_intent.status}')
        print(f'  TopUp Intent Created: {tx.topup_intent.created_at}')
        print(f'  TopUp Intent Expires: {tx.topup_intent.expires_at}')
        if tx.topup_intent.is_expired():
            print(f'  ⚠️  TopUp Intent is EXPIRED')
    
    print('\n' + '-' * 80)

# Check if monitoring has been run recently
print('\n\nMONITORING STATUS:')
print('-' * 80)
print('To check if monitoring is working, run: python manage.py monitor_deposits')
print('This should be run every 5 minutes via cron job')

# Check for addresses that should be monitored
active_addresses = DepositAddress.objects.filter(
    is_active=True,
    topup_intents__status__in=['pending', 'awaiting_confirmations']
).distinct()

print(f'\nActive deposit addresses needing monitoring: {active_addresses.count()}')
for addr in active_addresses:
    pending_intents = addr.topup_intents.filter(status__in=['pending', 'awaiting_confirmations'])
    print(f'  • {addr.address[:50]} - {pending_intents.count()} pending intents')

