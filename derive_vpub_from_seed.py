#!/usr/bin/env python
"""
Derive BIP84 account-level vpub from mnemonic seed.
This creates the correct vpub at m/84'/1'/0' for testnet.

⚠️  SECURITY: Only run this on a secure machine. Never share your seed!
"""
import sys
import os
import getpass

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')

# Load .env file explicitly BEFORE anything else
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        # Also manually read MNEMONIC if dotenv didn't load it
        if not os.environ.get('MNEMONIC'):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('MNEMONIC='):
                        value = line.split('=', 1)[1].strip().strip('"').strip("'")
                        os.environ['MNEMONIC'] = value
                        break
except ImportError:
    # Fallback: manual .env read
    try:
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('MNEMONIC='):
                        value = line.split('=', 1)[1].strip().strip('"').strip("'")
                        os.environ['MNEMONIC'] = value
                        break
    except:
        pass

try:
    import django
    django.setup()
except:
    pass

print("=" * 70)
print("DERIVE BIP84 ACCOUNT-LEVEL VPUB FROM SEED")
print("=" * 70)
print("\n⚠️  SECURITY WARNING:")
print("   - Only run this on a secure machine")
print("   - Never share your mnemonic seed")
print("   - We'll only derive the PUBLIC key (vpub), not private keys")
print("   - The vpub is safe to use (cannot spend funds)")
print("\n" + "=" * 70)

# Get mnemonic from command line, environment variable, or prompt user
if len(sys.argv) > 1:
    # Accept mnemonic as command-line arguments
    mnemonic = ' '.join(sys.argv[1:]).strip()
    print("✅ Using mnemonic from command-line arguments")
else:
    mnemonic = os.environ.get('MNEMONIC', '').strip()
    
    if mnemonic.startswith('MNEMONIC='):
        # Handle case where it's from .env file with MNEMONIC= prefix
        mnemonic = mnemonic.split('=', 1)[1].strip().strip('"').strip("'")
    
    if not mnemonic:
        print("\nEnter your 12 or 24 word mnemonic seed:")
        print("(Type all words separated by spaces, then press Enter)")
        print("Example: word1 word2 word3 ... word12")
        print("\n⚠️  For security, input is hidden (you won't see what you type)")
        print("(Or pass as arguments: python derive_vpub_from_seed.py word1 word2 ... word12)")
        mnemonic = getpass.getpass("\nMnemonic: ").strip()
    
    if not mnemonic:
        print("❌ No mnemonic provided")
        print("   Usage: python derive_vpub_from_seed.py word1 word2 ... word12")
        print("   Or set MNEMONIC environment variable")
        sys.exit(1)
    
    if os.environ.get('MNEMONIC'):
        print("✅ Using mnemonic from environment variable")
    else:
        print("✅ Using mnemonic from input")

# Count words
word_count = len(mnemonic.split())
if word_count not in [12, 15, 18, 21, 24]:
    print(f"\n❌ Invalid word count: {word_count}")
    print("   Mnemonic must be 12, 15, 18, 21, or 24 words")
    print("   You entered what appears to be {word_count} words")
    print("   Please check your mnemonic and try again")
    sys.exit(1)

print(f"✅ Received {word_count} words")

# Validate mnemonic (optional - will be validated during seed generation)
print("✅ Mnemonic received (will validate during derivation)")

# Derive BIP84 account-level vpub
print("\nDeriving BIP84 account-level vpub for testnet...")
print("Path: m/84'/1'/0' (testnet, account 0)")

try:
    from bip_utils import Bip39SeedGenerator, Bip84, Bip84Coins, Bip39Languages, Bip39MnemonicValidator
    
    # Validate mnemonic checksum first
    print("Validating mnemonic checksum...")
    try:
        validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)
        if not validator.Validate(mnemonic):
            print("⚠️  Checksum validation failed, but attempting derivation anyway...")
            print("   (This might fail if the mnemonic is invalid)")
    except Exception as e:
        print(f"⚠️  Could not validate checksum: {e}")
        print("   Attempting derivation anyway...")
    
    # Generate seed from mnemonic (auto-detects language)
    # Try English first (most common)
    try:
        seed_bytes = Bip39SeedGenerator(mnemonic, Bip39Languages.ENGLISH).Generate()
        print("✅ Seed generated from mnemonic (English)")
    except Exception as e:
        # If English fails, try without language (auto-detect)
        try:
            seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
            print("✅ Seed generated from mnemonic (auto-detect language)")
        except Exception as e2:
            print(f"❌ Failed to generate seed from mnemonic")
            print(f"   English error: {e}")
            print(f"   Auto-detect error: {e2}")
            print("\n💡 Common issues:")
            print("   • One word is misspelled (even slightly)")
            print("   • Words are in wrong order")
            print("   • Missing or extra word")
            print("   • Wrong language")
            print("\n   Run: python debug_mnemonic.py word1 word2 ... word12")
            print("   to identify which word is wrong")
            raise
    
    # Create BIP84 from seed (testnet)
    bip84 = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN_TESTNET)
    print("✅ BIP84 wallet created")
    
    # Derive to account level: m/84'/1'/0'
    account = bip84.Purpose().Coin().Account(0)
    print("✅ Derived to account level (m/84'/1'/0')")
    
    # Get the account-level extended public key (vpub)
    account_vpub = account.PublicKey().ToExtended()
    
    print("\n" + "=" * 70)
    print("✅ SUCCESS! Your account-level vpub:")
    print("=" * 70)
    print(f"\n{account_vpub}\n")
    print("=" * 70)
    
    # Verify it works by deriving a test address
    print("\nTesting address derivation...")
    test_addr = account.Change(0).AddressIndex(0).PublicKey().ToAddress()
    print(f"✅ Test address (index 0): {test_addr}")
    
    if test_addr.startswith('tb1'):
        print(f"✅ Address format correct (testnet bech32)")
    else:
        print(f"⚠️  Unexpected address format: {test_addr[:10]}...")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Copy the vpub above")
    print("2. Test it: python check_vpub.py <vpub>")
    print("3. Set it in database: btc_testnet.xpub = '<vpub>'")
    print("4. System will now derive tb1... addresses automatically!")
    print("\n" + "=" * 70)
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Install: pip install bip-utils")
    sys.exit(1)
except Exception as e:
    print(f"❌ Derivation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

