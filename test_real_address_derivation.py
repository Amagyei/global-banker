"""
Test real address derivation with xpub
Run this after setting DEFAULT_XPUB environment variable
"""
import os
from django.conf import settings
from wallet.utils import derive_address_from_xpub

print("=" * 60)
print("TESTING REAL ADDRESS DERIVATION")
print("=" * 60)

# Check environment variable
xpub_env = os.getenv('DEFAULT_XPUB', '')
xpub_settings = getattr(settings, 'DEFAULT_XPUB', '')

print(f"\n1. Checking xpub configuration...")
print(f"   Environment variable (DEFAULT_XPUB): {'Set' if xpub_env else 'Not set'} ({len(xpub_env)} chars)")
print(f"   Settings (DEFAULT_XPUB): {'Set' if xpub_settings else 'Not set'} ({len(xpub_settings)} chars)")

if xpub_env:
    print(f"   First 20 chars: {xpub_env[:20]}...")
elif xpub_settings:
    print(f"   First 20 chars: {xpub_settings[:20]}...")
else:
    print("   ⚠️  No xpub found in environment or settings")
    print("   Set it with: export DEFAULT_XPUB='your-xpub-here'")
    exit(1)

# Use the xpub from environment or settings
xpub = xpub_env or xpub_settings

# Test Bitcoin testnet address derivation
print(f"\n2. Testing Bitcoin testnet address derivation...")
try:
    # Derive first 5 addresses
    for i in range(5):
        address = derive_address_from_xpub(xpub, i, "btc", is_testnet=True)
        print(f"   Index {i}: {address}")
    print("   ✓ Address derivation successful!")
except Exception as e:
    print(f"   ✗ Error: {e}")
    print("   This might be because:")
    print("   - xpub format is incorrect (should be BIP84)")
    print("   - xpub is for mainnet but we're using testnet")
    print("   - xpub is for a different derivation path")

# Test mainnet (if xpub is mainnet)
print(f"\n3. Testing Bitcoin mainnet address derivation...")
try:
    address = derive_address_from_xpub(xpub, 0, "btc", is_testnet=False)
    print(f"   Index 0 (mainnet): {address}")
    print("   ✓ Mainnet derivation successful!")
except Exception as e:
    print(f"   ✗ Error: {e}")
    print("   (This is expected if xpub is for testnet)")

print("\n" + "=" * 60)
print("Next steps:")
print("1. If derivation works, create a top-up intent")
print("2. Send testnet BTC to the generated address")
print("3. Run: python manage.py monitor_deposits")
print("=" * 60)

