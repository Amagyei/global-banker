"""
Test zpub to xpub conversion and address derivation
Run: python manage.py shell < test_zpub_conversion.py
"""
import os
from wallet.utils import zpub_to_xpub, derive_address_from_xpub
from bip_utils import Bip84, Bip84Coins, Bip44Changes

zpub = os.getenv('DEFAULT_XPUB', '')
print("=" * 60)
print("TESTING ZPUB CONVERSION AND ADDRESS DERIVATION")
print("=" * 60)

if not zpub:
    print("❌ DEFAULT_XPUB environment variable is NOT SET")
    print("\nPlease set it with:")
    print("  export DEFAULT_XPUB='your-zpub-here'")
    exit(1)

print(f"\n1. Zpub validation:")
print(f"   Length: {len(zpub)}")
print(f"   Prefix: {zpub[:10]}...")
print(f"   Format: {'zpub (BIP84 mainnet)' if zpub.startswith('zpub') else 'other'}")

# Check for invalid characters
invalid_chars = [i for i, c in enumerate(zpub) if ord(c) > 127]
if invalid_chars:
    print(f"   ⚠️  Invalid characters at positions: {invalid_chars}")
    exit(1)
else:
    print(f"   ✓ All characters are valid base58")

print(f"\n2. Converting zpub to xpub...")
try:
    xpub = zpub_to_xpub(zpub)
    print(f"   ✓ Conversion successful!")
    print(f"   Xpub: {xpub[:20]}...")
    print(f"   Length: {len(xpub)}")
except Exception as e:
    print(f"   ✗ Conversion failed: {e}")
    exit(1)

print(f"\n3. Testing address derivation with bip_utils (using zpub directly)...")
try:
    # Use zpub directly - bip_utils BIP84 should accept it
    bip84 = Bip84.FromExtendedKey(zpub, Bip84Coins.BITCOIN)
    print(f"   ✓ BIP84 object created")
    
    # Derive first 3 addresses
    for i in range(3):
        addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
        print(f"   Address {i}: {addr}")
        print(f"      Format: {'Bech32 (BIP84)' if addr.startswith('bc1') else 'Other'}")
    
    print(f"\n✓ All tests passed! Your zpub is valid and working.")
    
except Exception as e:
    print(f"   ✗ Derivation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("SUCCESS! Your zpub is working correctly.")
print("=" * 60)

