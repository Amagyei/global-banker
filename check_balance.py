#!/usr/bin/env python
"""
Check wallet balance and verify on-chain transactions.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import Wallet, DepositAddress, TopUpIntent, OnChainTransaction
from wallet.blockchain import BlockchainMonitor
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone

User = get_user_model()

print("=" * 70)
print("WALLET BALANCE CHECKER")
print("=" * 70)

# Get user email from command line or use all users
user_email = None
if len(sys.argv) > 1:
    user_email = sys.argv[1]

if user_email:
    try:
        user = User.objects.get(email=user_email)
        users = [user]
    except User.DoesNotExist:
        print(f"\n❌ User '{user_email}' not found")
        sys.exit(1)
else:
    users = User.objects.all()

if not users.exists():
    print("\n❌ No users found")
    sys.exit(0)

print(f"\nChecking {users.count()} user(s)...\n")

for user in users:
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={'currency_code': 'USD', 'balance_minor': 0}
    )
    
    print(f"{'=' * 70}")
    print(f"User: {user.email}")
    print(f"{'=' * 70}")
    print(f"\n💰 Wallet Balance:")
    print(f"  Current: ${wallet.balance_minor / 100:.2f} USD")
    print(f"  Pending: ${wallet.pending_minor / 100:.2f} USD")
    print(f"  Total:   ${(wallet.balance_minor + wallet.pending_minor) / 100:.2f} USD")
    
    # Check deposit addresses
    addresses = DepositAddress.objects.filter(user=user, is_active=True).select_related('network')
    print(f"\n📍 Active Deposit Addresses: {addresses.count()}")
    
    if addresses.exists():
        for addr in addresses:
            print(f"\n  Address: {addr.address}")
            print(f"    Network: {addr.network.name} ({'testnet' if addr.network.effective_is_testnet else 'mainnet'})")
            print(f"    Index: {addr.index}")
            print(f"    Created: {addr.created_at}")
            
            # Check for top-up intents
            topups = TopUpIntent.objects.filter(deposit_address=addr).order_by('-created_at')
            if topups.exists():
                print(f"    Top-ups: {topups.count()}")
                for topup in topups[:3]:
                    status_icon = "✅" if topup.status == 'succeeded' else "⏳" if topup.status == 'pending' else "❌"
                    expired = " (EXPIRED)" if topup.expires_at and topup.expires_at < timezone.now() else ""
                    print(f"      {status_icon} ${topup.amount_minor / 100:.2f} - {topup.status}{expired}")
            
            # Check on-chain transactions
            onchain_txs = OnChainTransaction.objects.filter(to_address=addr.address).order_by('-occurred_at')
            if onchain_txs.exists():
                print(f"    On-chain transactions: {onchain_txs.count()}")
                for tx in onchain_txs[:3]:
                    status_icon = "✅" if tx.status == 'confirmed' else "⏳"
                    print(f"      {status_icon} {tx.amount_atomic / (10 ** addr.network.decimals):.8f} {addr.network.native_symbol}")
                    print(f"         Status: {tx.status} ({tx.confirmations}/{tx.required_confirmations} confirmations)")
                    print(f"         TX: {tx.tx_hash[:30]}...")
            else:
                # Check blockchain directly
                print(f"    Checking blockchain...")
                try:
                    monitor = BlockchainMonitor(addr.network)
                    txs = monitor.get_address_transactions(addr.address)
                    if txs:
                        print(f"    ✅ Found {len(txs)} transaction(s) on blockchain (not yet in database)")
                        print(f"    💡 Run: python manage.py monitor_deposits")
                    else:
                        print(f"    ❌ No transactions found on blockchain")
                        if addr.network.effective_is_testnet:
                            print(f"    💡 Check: https://blockstream.info/testnet/address/{addr.address}")
                        else:
                            print(f"    💡 Check: https://blockstream.info/address/{addr.address}")
                except Exception as e:
                    print(f"    ⚠️  Error checking blockchain: {e}")
    
    # Check all on-chain transactions
    all_onchain = OnChainTransaction.objects.filter(user=user).order_by('-occurred_at')
    if all_onchain.exists():
        print(f"\n📊 All On-Chain Transactions: {all_onchain.count()}")
        confirmed_total = sum(tx.amount_minor for tx in all_onchain if tx.status == 'confirmed')
        pending_total = sum(tx.amount_minor for tx in all_onchain if tx.status == 'pending')
        
        print(f"  Confirmed: ${confirmed_total / 100:.2f} USD ({sum(1 for tx in all_onchain if tx.status == 'confirmed')} tx)")
        print(f"  Pending:   ${pending_total / 100:.2f} USD ({sum(1 for tx in all_onchain if tx.status == 'pending')} tx)")
        
        if confirmed_total > 0:
            print(f"\n  💡 Expected balance: ${confirmed_total / 100:.2f} USD")
            print(f"  💡 Actual balance:   ${wallet.balance_minor / 100:.2f} USD")
            if confirmed_total != wallet.balance_minor:
                diff = confirmed_total - wallet.balance_minor
                print(f"  ⚠️  Difference: ${diff / 100:.2f} USD")
                if diff > 0:
                    print(f"  💡 Balance might not be credited yet - check top-up intents")
    
    # Check pending top-ups
    pending_topups = TopUpIntent.objects.filter(user=user, status='pending')
    if pending_topups.exists():
        print(f"\n⏳ Pending Top-Ups: {pending_topups.count()}")
        total_pending = sum(tup.amount_minor for tup in pending_topups)
        print(f"  Total pending: ${total_pending / 100:.2f} USD")
        print(f"  💡 Run: python manage.py monitor_deposits")
    
    print()

print("=" * 70)
print("💡 To check for new transactions:")
print("   python manage.py monitor_deposits")
print("=" * 70)

