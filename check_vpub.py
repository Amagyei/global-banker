#!/usr/bin/env python
"""
Diagnostic script to check vpub depth and derive test addresses.
Run: python check_vpub.py <your_vpub>
"""
import sys
import os

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')

try:
    import django
    django.setup()
except:
    pass

vpub = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TEST_VPUB', '')

if not vpub:
    print("Usage: python check_vpub.py <vpub>")
    print("   Or: TEST_VPUB=<vpub> python check_vpub.py")
    sys.exit(1)

print("=" * 70)
print("VPUB DIAGNOSTIC CHECK")
print("=" * 70)
print(f"\nVpub: {vpub[:40]}...{vpub[-20:]}")
print(f"Prefix: {vpub[:4]}")
print(f"Length: {len(vpub)}")

# Check for invalid characters
invalid_chars = [c for c in vpub if c not in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz']
if invalid_chars:
    print(f"\n❌ INVALID BASE58 CHARACTERS: {invalid_chars}")
    print("   Base58 excludes: 0, O, I, l")
    sys.exit(1)
else:
    print("✅ Base58 characters valid")

# Try bip_utils BIP84
print("\n" + "-" * 70)
print("1. Testing with bip_utils BIP84")
print("-" * 70)

try:
    from bip_utils import Bip84, Bip84Coins, Bip44Changes
    
    bip84 = Bip84.FromExtendedKey(vpub, Bip84Coins.BITCOIN_TESTNET)
    depth = bip84.Depth()
    
    print(f"✅ Bip84 created successfully!")
    print(f"   Depth: {depth}")
    print(f"   Expected: 3 (account level m/84'/1'/0')")
    
    if depth == 3:
        print(f"   ✅ CORRECT DEPTH - Account level!")
        
        # Try deriving addresses
        print(f"\n   Deriving test addresses...")
        for i in [0, 1, 2, 5]:
            try:
                addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
                status = "✅" if addr.startswith('tb1') else "⚠️"
                print(f"   {status} Index {i}: {addr}")
            except Exception as e:
                print(f"   ❌ Index {i}: {e}")
        
        print(f"\n✅ SUCCESS! Your vpub is valid and ready to use.")
        print(f"   You can now set it in the database and start receiving deposits.")
        
    elif depth < 3:
        print(f"   ❌ DEPTH TOO LOW (depth {depth})")
        print(f"   The vpub is at depth {depth}, but needs to be at depth 3 (account level).")
        print(f"   SOLUTION: Re-export the vpub from your wallet at the ACCOUNT level.")
        print(f"   Path needed: m/84'/1'/0' (for testnet)")
    elif depth > 5:
        print(f"   ❌ DEPTH TOO HIGH (depth {depth})")
        print(f"   The vpub is beyond address index level.")
        print(f"   SOLUTION: Re-export the vpub from your wallet at the ACCOUNT level.")
        print(f"   Path needed: m/84'/1'/0' (for testnet)")
    else:
        print(f"   ⚠️  DEPTH {depth} - May work, but not standard account level")
        
except Exception as e:
    print(f"❌ Bip84 failed: {type(e).__name__}: {e}")
    if "Depth" in str(e) or "depth" in str(e).lower():
        print(f"\n   This confirms the vpub is NOT at account level (depth 3).")
        print(f"   SOLUTION: Re-export vpub from wallet at account level (m/84'/1'/0')")

# Try generic BIP32 parse to check depth
print("\n" + "-" * 70)
print("2. Testing with generic BIP32 parse (to check depth)")
print("-" * 70)

depth = None
try:
    from bip_utils.bip.bip32.bip32_base import Bip32Base
    from bip_utils.bip.bip32.bip32_key_net_versions import Bip32KeyNetVersions
    
    key_net_versions = Bip32KeyNetVersions.TestNetPublic()
    bip32 = Bip32Base.FromExtendedKey(vpub, key_net_versions)
    depth = bip32.Depth()
    fingerprint = bip32.ParentFingerPrint()
    
    print(f"✅ Generic Bip32 parse OK")
    print(f"   Depth: {depth}")
    print(f"   Parent Fingerprint: {fingerprint.hex() if fingerprint else 'N/A'}")
    
    if depth == 3:
        print(f"   ✅ This confirms depth 3 (account level)")
    else:
        print(f"   ⚠️  Depth {depth} - Not at account level (expected 3)")
        
except ImportError as e:
    print(f"⚠️  Could not import Bip32Base (version difference): {e}")
    print(f"   This is OK - the Bip84 test above already confirmed the issue")
except Exception as e:
    print(f"❌ Generic Bip32 parse failed: {type(e).__name__}: {e}")

# Summary and recommendations
print("\n" + "=" * 70)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 70)

# Check if we got a valid depth
if depth is not None and depth == 3:
    print("\n✅ Your vpub is CORRECT and ready to use!")
    print("\nNext steps:")
    print("  1. Set it in database: btc_testnet.xpub = '<your_vpub>'")
    print("  2. Test: python test_your_testnet_xpub.py <your_vpub>")
    print("  3. Create top-ups via frontend")
    print("  4. System will derive tb1... addresses automatically")
elif depth is not None:
    print(f"\n❌ Your vpub is at depth {depth}, but needs to be at depth 3.")
    print("\nSOLUTION: Re-export from your wallet")
    print("  1. Open Electrum wallet")
    print("  2. Go to: Wallet → Information")
    print("  3. Look for 'Master Public Key' or 'Account XPUB'")
    print("  4. Export at ACCOUNT level (path: m/84'/1'/0')")
    print("  5. Make sure it's vpub format (testnet BIP84)")
    print("  6. Re-run this script with the new vpub")
else:
    print(f"\n❌ Your vpub is NOT at account level (depth 3).")
    print("\nThe Bip84 test confirmed the vpub depth is incorrect.")
    print("\nSOLUTION: Re-export from your wallet")
    print("  1. Open Electrum wallet")
    print("  2. Go to: Wallet → Information")
    print("  3. Look for 'Master Public Key' or 'Account XPUB'")
    print("  4. Export at ACCOUNT level (path: m/84'/1'/0')")
    print("  5. Make sure it's vpub format (testnet BIP84)")
    print("  6. Re-run this script with the new vpub")

print("\n" + "=" * 70)

