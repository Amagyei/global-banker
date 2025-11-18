#!/usr/bin/env python
"""
Check deposit addresses and verify transactions on blockchain.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import DepositAddress, TopUpIntent, OnChainTransaction
from wallet.blockchain import BlockchainMonitor
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("DEPOSIT ADDRESS CHECKER")
print("=" * 70)

# Get all active deposit addresses
addresses = DepositAddress.objects.filter(is_active=True).select_related('user', 'network')

if not addresses.exists():
    print("\n❌ No active deposit addresses found")
    sys.exit(0)

print(f"\nFound {addresses.count()} active deposit address(es):\n")

for addr in addresses:
    print(f"User: {addr.user.email}")
    print(f"Network: {addr.network.name} ({'testnet' if addr.network.is_testnet else 'mainnet'})")
    print(f"Address: {addr.address}")
    print(f"Index: {addr.index}")
    print(f"Created: {addr.created_at}")
    
    # Check for top-up intents
    topups = TopUpIntent.objects.filter(deposit_address=addr).order_by('-created_at')
    if topups.exists():
        print(f"\n  Top-up Intents ({topups.count()}):")
        for topup in topups[:5]:  # Show last 5
            print(f"    • Amount: ${topup.amount_minor / 100:.2f} USD")
            print(f"      Status: {topup.status}")
            print(f"      Created: {topup.created_at}")
            print(f"      Expires: {topup.expires_at}")
            if topup.expires_at and topup.expires_at < django.utils.timezone.now():
                print(f"      ⚠️  EXPIRED")
    
    # Check for on-chain transactions
    onchain_txs = OnChainTransaction.objects.filter(to_address=addr.address).order_by('-occurred_at')
    if onchain_txs.exists():
        print(f"\n  On-chain Transactions ({onchain_txs.count()}):")
        for tx in onchain_txs[:5]:  # Show last 5
            print(f"    • TX Hash: {tx.tx_hash[:20]}...")
            print(f"      Amount: {tx.amount_atomic / (10 ** addr.network.decimals):.8f} {addr.network.native_symbol}")
            print(f"      Status: {tx.status}")
            print(f"      Confirmations: {tx.confirmations}/{tx.required_confirmations}")
            print(f"      Occurred: {tx.occurred_at}")
    else:
        print(f"\n  ⚠️  No on-chain transactions found")
    
    # Check blockchain directly
    print(f"\n  Checking blockchain directly...")
    try:
        monitor = BlockchainMonitor(addr.network)
        txs = monitor.get_address_transactions(addr.address)
        
        if txs:
            print(f"  ✅ Found {len(txs)} transaction(s) on blockchain:")
            for tx in txs[:3]:  # Show first 3
                txid = tx.get('txid') or tx.get('hash', 'unknown')
                status = tx.get('status', {})
                confirmed = status.get('confirmed', False)
                block_height = status.get('block_height')
                
                print(f"    • TX: {txid[:20]}...")
                print(f"      Confirmed: {confirmed}")
                if block_height:
                    print(f"      Block: {block_height}")
                
                # Check if we have this in our database
                if OnChainTransaction.objects.filter(tx_hash=txid).exists():
                    print(f"      ✅ Already in database")
                else:
                    print(f"      ⚠️  NOT in database - run monitor_deposits command!")
        else:
            print(f"  ❌ No transactions found on blockchain")
            print(f"  💡 Check the address on block explorer:")
            if addr.network.is_testnet:
                print(f"     https://blockstream.info/testnet/address/{addr.address}")
            else:
                print(f"     https://blockstream.info/address/{addr.address}")
    except Exception as e:
        print(f"  ❌ Error checking blockchain: {e}")
    
    print("\n" + "-" * 70)

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("1. Verify addresses on block explorer (links above)")
print("2. If transactions exist on blockchain but not in database:")
print("   python manage.py monitor_deposits")
print("3. If no transactions found, verify:")
print("   • Address is correct")
print("   • Transaction was sent to the right network (testnet/mainnet)")
print("   • Transaction was actually broadcast")

