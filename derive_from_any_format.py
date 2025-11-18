#!/usr/bin/env python
"""
Derive vpub from mnemonic, trying multiple formats:
- BIP39 (standard)
- Electrum old format (non-BIP39)
- BIP32 direct derivation (if mnemonic is actually a seed)
"""
import sys
import os
import hashlib

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')

try:
    import django
    django.setup()
except:
    pass

print("=" * 70)
print("DERIVE VPUB FROM MNEMONIC (MULTIPLE FORMATS)")
print("=" * 70)
print("\nThis will try:")
print("  1. BIP39 standard (with checksum)")
print("  2. BIP39 without strict checksum (if possible)")
print("  3. Direct seed derivation (if mnemonic is actually hex/bytes)")
print("\n" + "=" * 70)

# Get mnemonic from command line
if len(sys.argv) < 2:
    print("\nUsage: python derive_from_any_format.py word1 word2 ... word12")
    print("   Or: python derive_from_any_format.py")
    print("       (then paste mnemonic when prompted)")
    sys.exit(1)

words = sys.argv[1:]
mnemonic = " ".join(words)

print(f"\nMnemonic ({len(words)} words):")
print(f"  {mnemonic[:60]}..." if len(mnemonic) > 60 else f"  {mnemonic}")

# Try BIP39 standard first
print("\n" + "-" * 70)
print("1. Trying BIP39 standard derivation...")
print("-" * 70)

try:
    from bip_utils import Bip39SeedGenerator, Bip84, Bip84Coins, Bip39Languages, Bip39MnemonicValidator
    
    # Try with checksum validation
    validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)
    if validator.Validate(mnemonic):
        print("✅ BIP39 checksum is valid!")
        seed_bytes = Bip39SeedGenerator(mnemonic, Bip39Languages.ENGLISH).Generate()
        print("✅ Seed generated from BIP39 mnemonic")
        
        # Derive BIP84 vpub
        bip84 = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN_TESTNET)
        account = bip84.Purpose().Coin().Account(0)
        vpub = account.PublicKey().ToExtended()
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS! BIP84 account-level vpub (m/84'/1'/0'):")
        print("=" * 70)
        print(f"\n{vpub}\n")
        print("=" * 70)
        
        # Test address
        test_addr = account.Change(0).AddressIndex(0).PublicKey().ToAddress()
        print(f"\n✅ Test address (index 0): {test_addr}")
        sys.exit(0)
    else:
        print("❌ BIP39 checksum validation failed")
        print("   Trying alternative methods...")
except Exception as e:
    print(f"❌ BIP39 standard failed: {e}")

# Try BIP39 without strict validation (decode directly)
print("\n" + "-" * 70)
print("2. Trying BIP39 decode without strict checksum...")
print("-" * 70)

try:
    from bip_utils.bip.bip39 import Bip39MnemonicDecoder
    from bip_utils import Bip39Languages
    
    decoder = Bip39MnemonicDecoder(Bip39Languages.ENGLISH)
    
    # Try to decode without validation
    # This is risky but might work if checksum is just slightly off
    try:
        # Decode the mnemonic to get the entropy
        mnemonic_bin = decoder.Decode(mnemonic)
        print("✅ Successfully decoded mnemonic (ignoring checksum)")
        print("   ⚠️  WARNING: Checksum was invalid, but proceeding anyway")
        
        # Generate seed from decoded mnemonic
        # We need to use PBKDF2 with the mnemonic as password
        import hashlib
        import hmac
        
        # BIP39 seed generation: PBKDF2(mnemonic, "mnemonic" + passphrase, 2048, 64)
        passphrase = ""  # No passphrase
        seed_bytes = hashlib.pbkdf2_hmac('sha512', mnemonic.encode('utf-8'), 
                                        b'mnemonic' + passphrase.encode('utf-8'), 
                                        2048)
        print("✅ Seed generated from decoded mnemonic")
        
        # Derive BIP84 vpub
        bip84 = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN_TESTNET)
        account = bip84.Purpose().Coin().Account(0)
        vpub = account.PublicKey().ToExtended()
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS! BIP84 account-level vpub (m/84'/1'/0'):")
        print("=" * 70)
        print(f"\n{vpub}\n")
        print("=" * 70)
        
        # Test address
        test_addr = account.Change(0).AddressIndex(0).PublicKey().ToAddress()
        print(f"\n✅ Test address (index 0): {test_addr}")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Decode without checksum failed: {e}")
except Exception as e:
    print(f"❌ Alternative decode method failed: {e}")

# Try BIP32 direct derivation (if mnemonic is actually a seed in hex)
print("\n" + "-" * 70)
print("3. Trying BIP32 direct derivation...")
print("-" * 70)
print("   (This assumes the 'mnemonic' is actually a seed or xpub)")

# Check if it looks like hex
if all(c in '0123456789abcdefABCDEF' for c in mnemonic.replace(' ', '')):
    print("   ⚠️  Input looks like hex, but BIP32 needs a seed, not hex directly")
    print("   Skipping BIP32 direct derivation")

# Final attempt: Try to fix checksum and retry
print("\n" + "-" * 70)
print("4. All methods failed")
print("-" * 70)
print("\n💡 The mnemonic checksum error means one word is wrong.")
print("   The checksum is a security feature that detects typos.")
print("\n💡 Options:")
print("   1. Run: python fix_checksum.py word1 word2 ... word12")
print("      (This will try to find and fix the typo)")
print("   2. Run: python debug_mnemonic.py word1 word2 ... word12")
print("      (This will show which words are suspicious)")
print("   3. Double-check your mnemonic source")
print("      (One word is misspelled or wrong)")
print("\n💡 Note: BIP32 is a derivation standard, not a mnemonic format.")
print("   Mnemonics are typically BIP39 format (12/24 words).")
print("   BIP32/BIP84 are used AFTER the mnemonic is converted to a seed.")

sys.exit(1)

