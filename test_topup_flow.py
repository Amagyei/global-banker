"""
Test script for the full top-up flow
Run this in Django shell: python manage.py shell < test_topup_flow.py
Or copy-paste into shell
"""
from accounts.models import User
from wallet.models import CryptoNetwork, TopUpIntent, Wallet, DepositAddress, OnChainTransaction
from wallet.utils import create_topup_intent
from wallet.blockchain import BlockchainMonitor
from transactions.models import Transaction
from django.conf import settings
from django.utils import timezone

print("=" * 60)
print("TESTING FULL TOP-UP FLOW")
print("=" * 60)

# Step 1: Get or create test user
print("\n1. Setting up test user...")
user, created = User.objects.get_or_create(
    email='test@example.com',
    defaults={
        'username': 'testuser',
        'first_name': 'Test',
        'last_name': 'User'
    }
)
if created:
    user.set_password('testpass123')
    user.save()
    print(f"   ✓ Created user: {user.email}")
else:
    print(f"   ✓ Using existing user: {user.email}")

# Step 2: Get Bitcoin Testnet network
print("\n2. Getting Bitcoin Testnet network...")
network = CryptoNetwork.objects.filter(key='btc', is_active=True).first()
if not network:
    print("   ✗ Bitcoin Testnet network not found!")
    exit(1)
print(f"   ✓ Network: {network.name} ({network.key})")
print(f"   ✓ Testnet: {network.is_testnet}")
print(f"   ✓ Xpub configured: {'Yes' if network.xpub or getattr(settings, 'DEFAULT_XPUB', '') else 'No'}")

# Step 3: Check current wallet balance
print("\n3. Checking current wallet balance...")
wallet, _ = Wallet.objects.get_or_create(
    user=user,
    defaults={'currency_code': 'USD', 'balance_minor': 0}
)
print(f"   ✓ Current balance: ${wallet.balance_minor / 100:.2f} USD")

# Step 4: Create top-up intent for $20
print("\n4. Creating top-up intent for $20...")
amount_minor = 2000  # $20.00 in cents
topup = create_topup_intent(user, amount_minor, network, ttl_minutes=30)
print(f"   ✓ Top-up intent created: {topup.id}")
print(f"   ✓ Status: {topup.get_status_display()}")
print(f"   ✓ Amount: ${topup.amount_minor / 100:.2f} {topup.currency_code}")
print(f"   ✓ Deposit address: {topup.deposit_address.address}")
print(f"   ✓ Expires at: {topup.expires_at}")

# Step 5: Check if address was derived correctly
print("\n5. Verifying deposit address...")
deposit_address = topup.deposit_address
print(f"   ✓ Address index: {deposit_address.index}")
print(f"   ✓ Address: {deposit_address.address}")
print(f"   ✓ Network: {deposit_address.network.name}")
print(f"   ✓ Is active: {deposit_address.is_active}")

# Step 6: Check test mode
test_mode = getattr(settings, 'WALLET_TEST_MODE', False)
print(f"\n6. Test mode: {'ENABLED' if test_mode else 'DISABLED'}")
if test_mode:
    print("   ℹ️  In test mode, deposits will be simulated automatically")
else:
    print("   ℹ️  In production mode, send real crypto to the address above")

# Step 7: Monitor for deposits
print("\n7. Monitoring for deposits...")
monitor = BlockchainMonitor(network)
found = monitor.check_deposit_address(deposit_address, topup)

if found:
    print("   ✓ Transaction found!")
    
    # Check top-up status
    topup.refresh_from_db()
    print(f"   ✓ Top-up status: {topup.get_status_display()}")
    
    # Check wallet balance
    wallet.refresh_from_db()
    print(f"   ✓ New wallet balance: ${wallet.balance_minor / 100:.2f} USD")
    
    # Check for on-chain transaction
    onchain_tx = OnChainTransaction.objects.filter(
        topup_intent=topup,
        status='confirmed'
    ).first()
    if onchain_tx:
        print(f"   ✓ On-chain transaction: {onchain_tx.tx_hash[:20]}...")
        print(f"   ✓ Amount received: {onchain_tx.amount_atomic / (10**network.decimals)} {network.native_symbol}")
        print(f"   ✓ Converted to: ${onchain_tx.amount_minor / 100:.2f} USD")
        print(f"   ✓ Confirmations: {onchain_tx.confirmations}/{onchain_tx.required_confirmations}")
    
    # Check for transaction record
    tx = Transaction.objects.filter(
        user=user,
        related_topup_intent_id=topup.id
    ).first()
    if tx:
        print(f"   ✓ Transaction record created: {tx.id}")
        print(f"   ✓ Amount: ${tx.amount_minor / 100:.2f} {tx.currency_code}")
        print(f"   ✓ Status: {tx.get_status_display()}")
else:
    print("   ⚠️  No transaction found yet")
    if test_mode:
        print("   ℹ️  In test mode, you may need to wait a moment or run monitor_deposits again")
    else:
        print(f"   ℹ️  Send testnet BTC to: {deposit_address.address}")
        print("   ℹ️  Then run: python manage.py monitor_deposits")

# Step 8: Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"User: {user.email}")
print(f"Network: {network.name}")
print(f"Deposit Address: {deposit_address.address}")
print(f"Top-up Amount: ${amount_minor / 100:.2f} USD")
print(f"Top-up Status: {topup.get_status_display()}")
print(f"Wallet Balance: ${wallet.balance_minor / 100:.2f} USD")
print(f"Test Mode: {'ON' if test_mode else 'OFF'}")
print("=" * 60)

print("\n✅ Test complete!")
print("\nNext steps:")
if not found:
    if test_mode:
        print("  - Run: python manage.py monitor_deposits")
        print("  - Or wait a moment and check again")
    else:
        print(f"  - Send testnet BTC to: {deposit_address.address}")
        print("  - Use a Bitcoin testnet faucet: https://bitcoinfaucet.uo1.net/")
        print("  - Then run: python manage.py monitor_deposits")
print("  - Check wallet balance: Wallet.objects.get(user=user).balance_minor / 100")

