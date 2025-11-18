"""
Test full wallet integration with real zpub
"""
from wallet.models import CryptoNetwork, Wallet, TopUpIntent
from wallet.utils import create_topup_intent
from accounts.models import User
from django.conf import settings

print("=" * 60)
print("FULL WALLET INTEGRATION TEST")
print("=" * 60)

# Get user and network
user = User.objects.first()
network = CryptoNetwork.objects.filter(key='btc', is_testnet=False).first()

print(f"\n1. Configuration:")
print(f"   User: {user.email}")
print(f"   Network: {network.name} (Testnet: {network.is_testnet})")
print(f"   Test Mode: {getattr(settings, 'WALLET_TEST_MODE', False)}")
print(f"   Xpub set: {bool(getattr(settings, 'DEFAULT_XPUB', ''))}")

# Check wallet
wallet, _ = Wallet.objects.get_or_create(
    user=user,
    defaults={'currency_code': 'USD', 'balance_minor': 0}
)
print(f"\n2. Wallet:")
print(f"   Balance: ${wallet.balance_minor / 100:.2f} USD")

# Create top-up intent
print(f"\n3. Creating top-up intent for $50...")
topup = create_topup_intent(user, 5000, network, ttl_minutes=30)
print(f"   ✓ Top-up created: {topup.id}")
print(f"   ✓ Amount: ${topup.amount_minor / 100:.2f} {topup.currency_code}")
print(f"   ✓ Deposit address: {topup.deposit_address.address}")
print(f"   ✓ Address format: {'Bech32 (BIP84)' if topup.deposit_address.address.startswith('bc1') else 'Other'}")
print(f"   ✓ Address index: {topup.deposit_address.index}")
print(f"   ✓ Status: {topup.get_status_display()}")

print(f"\n" + "=" * 60)
print("✓ Integration test complete!")
print("=" * 60)
print(f"\nNext steps:")
print(f"1. Send Bitcoin to: {topup.deposit_address.address}")
print(f"2. Run: python manage.py monitor_deposits")
print(f"3. Check wallet balance updates")

