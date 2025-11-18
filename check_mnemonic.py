#!/usr/bin/env python
"""
Check mnemonic for typos and suggest corrections.
Helps identify which word might be wrong.
"""
import sys
from bip_utils import Bip39MnemonicValidator, Bip39Languages, Bip39WordsNum

def check_mnemonic(mnemonic):
    """Check mnemonic and suggest fixes"""
    words = mnemonic.strip().split()
    word_count = len(words)
    
    print("=" * 70)
    print("MNEMONIC CHECKER")
    print("=" * 70)
    print(f"\nWord count: {word_count}")
    
    if word_count not in [12, 15, 18, 21, 24]:
        print(f"❌ Invalid word count. Must be 12, 15, 18, 21, or 24 words")
        return False
    
    # Check each word against BIP39 wordlist
    print("\nChecking words against BIP39 wordlist...")
    from bip_utils.bip.bip39.bip39_wordlist import Bip39WordList
    
    invalid_words = []
    for i, word in enumerate(words, 1):
        word_lower = word.lower().strip()
        if word_lower not in Bip39WordList(Bip39Languages.ENGLISH).GetWordList():
            invalid_words.append((i, word))
            print(f"  ❌ Word {i}: '{word}' - NOT in BIP39 wordlist")
        else:
            print(f"  ✅ Word {i}: '{word}'")
    
    if invalid_words:
        print(f"\n❌ Found {len(invalid_words)} invalid word(s)")
        print("\nSuggestions:")
        from difflib import get_close_matches
        wordlist = Bip39WordList(Bip39Languages.ENGLISH).GetWordList()
        
        for pos, word in invalid_words:
            suggestions = get_close_matches(word.lower(), wordlist, n=5, cutoff=0.6)
            if suggestions:
                print(f"  Word {pos} '{word}' might be: {', '.join(suggestions)}")
            else:
                print(f"  Word {pos} '{word}' - no close matches found")
        return False
    
    # Try to validate checksum
    print("\nValidating checksum...")
    try:
        validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)
        if validator.Validate(mnemonic):
            print("✅ Mnemonic is valid!")
            return True
        else:
            print("❌ Mnemonic validation failed")
            return False
    except Exception as e:
        print(f"❌ Checksum error: {e}")
        print("\nThis usually means:")
        print("  • One word is misspelled")
        print("  • Words are in wrong order")
        print("  • Mnemonic is incomplete")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        mnemonic = ' '.join(sys.argv[1:])
    else:
        print("Usage: python check_mnemonic.py <word1> <word2> ... <word12>")
        print("   Or enter mnemonic when prompted:")
        mnemonic = input("Mnemonic: ").strip()
    
    if not mnemonic:
        print("❌ No mnemonic provided")
        sys.exit(1)
    
    if check_mnemonic(mnemonic):
        print("\n✅ Your mnemonic is valid and ready to use!")
        print("   You can now run: python derive_vpub_from_seed.py")
    else:
        print("\n❌ Please fix the errors above and try again")

