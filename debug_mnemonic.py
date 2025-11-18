#!/usr/bin/env python
"""
Debug mnemonic to find the exact issue causing checksum failure.
"""
import sys

# Get mnemonic from command line
if len(sys.argv) < 2:
    print("Usage: python debug_mnemonic.py <word1> <word2> ... <word12>")
    print("   Or: python debug_mnemonic.py 'word1 word2 ... word12'")
    sys.exit(1)

# Join all arguments (handles both formats)
mnemonic = ' '.join(sys.argv[1:]).strip()

# Remove quotes if present
if mnemonic.startswith("'") and mnemonic.endswith("'"):
    mnemonic = mnemonic[1:-1]
if mnemonic.startswith('"') and mnemonic.endswith('"'):
    mnemonic = mnemonic[1:-1]

words = mnemonic.split()
print("=" * 70)
print("MNEMONIC DEBUG")
print("=" * 70)
print(f"\nRaw input: {mnemonic[:50]}...")
print(f"Word count: {len(words)}")
print(f"\nWords:")
for i, word in enumerate(words, 1):
    print(f"  {i:2d}. '{word}' (length: {len(word)})")

# Check against BIP39 wordlist
print("\n" + "-" * 70)
print("Checking against BIP39 wordlist...")
print("-" * 70)

from bip_utils import Bip39Languages
from difflib import get_close_matches

# Get BIP39 wordlist using decoder
try:
    from bip_utils.bip.bip39 import Bip39MnemonicDecoder
    decoder = Bip39MnemonicDecoder(Bip39Languages.ENGLISH)
    wordlist_obj = decoder.m_words_list
    # Build wordlist by iterating through indices
    wordlist = []
    for i in range(wordlist_obj.Length()):
        wordlist.append(wordlist_obj.GetWordAtIdx(i))
    print(f"✅ Loaded BIP39 wordlist ({len(wordlist)} words)")
except Exception as e:
    print(f"⚠️  Could not load wordlist: {e}")
    wordlist = None
invalid = []
suspicious = []

if wordlist:
    for i, word in enumerate(words, 1):
        word_lower = word.lower().strip()
        
        # Check for common issues
        issues = []
        if word != word_lower:
            issues.append("has uppercase")
        if ' ' in word:
            issues.append("contains space")
        if not word_lower:
            issues.append("empty")
        
        if word_lower not in wordlist:
            invalid.append((i, word, issues))
            suggestions = get_close_matches(word_lower, wordlist, n=5, cutoff=0.5)
            print(f"❌ Word {i:2d}: '{word}' - NOT in BIP39 wordlist")
            if issues:
                print(f"      Issues: {', '.join(issues)}")
            if suggestions:
                print(f"      → Try: {', '.join(suggestions)}")
        else:
            # Check for close typos
            close = get_close_matches(word_lower, wordlist, n=3, cutoff=0.85)
            if len(close) > 1:
                suspicious.append((i, word, [c for c in close if c != word_lower]))
            print(f"✅ Word {i:2d}: '{word}'")
else:
    # Fallback: just show words and try to validate
    print("⚠️  Using fallback validation (wordlist not available)")
    for i, word in enumerate(words, 1):
        print(f"  {i:2d}. '{word}'")
    
    # Try to validate with bip_utils directly
    try:
        from bip_utils import Bip39MnemonicValidator
        validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)
        if validator.Validate(mnemonic):
            print("\n✅ Mnemonic is valid!")
        else:
            print("\n❌ Mnemonic validation failed")
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        print("   This confirms there's an issue with the mnemonic")

if invalid:
    print("\n" + "=" * 70)
    print(f"❌ FOUND {len(invalid)} INVALID WORD(S)")
    print("=" * 70)
    print("\nThese words are NOT in the BIP39 wordlist:")
    for pos, word, issues in invalid:
        suggestions = get_close_matches(word.lower(), wordlist, n=5, cutoff=0.5)
        print(f"\n  Position {pos}: '{word}'")
        if issues:
            print(f"    Issues: {', '.join(issues)}")
        if suggestions:
            print(f"    Suggestions: {', '.join(suggestions)}")
    
    print("\n💡 Fix these words and try again")
elif suspicious:
    print("\n" + "=" * 70)
    print("⚠️  SUSPICIOUS WORDS (might be typos)")
    print("=" * 70)
    for pos, word, similar in suspicious:
        if similar:
            print(f"  Position {pos}: '{word}' - similar to: {', '.join(similar)}")
            print(f"    → Double-check spelling!")
else:
    print("\n" + "=" * 70)
    print("✅ ALL WORDS ARE VALID BIP39 WORDS")
    print("=" * 70)
    
    # Try to validate checksum
    print("\nTesting checksum...")
    try:
        from bip_utils import Bip39MnemonicValidator, Bip39Languages
        validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)
        if validator.Validate(mnemonic):
            print("✅ Checksum is VALID!")
            print("   Your mnemonic is correct!")
        else:
            print("❌ Checksum validation failed")
            print("   This is strange - all words are valid but checksum fails")
            print("   Possible causes:")
            print("     • Words are in wrong order")
            print("     • Missing or extra word")
            print("     • Very subtle typo (e.g., 'abandn' vs 'abandon')")
    except Exception as e:
        print(f"❌ Checksum error: {e}")
        print("\nThe checksum error means one word is wrong.")
        print("Even though all words are in the wordlist, one might be:")
        print("  • A very close typo (e.g., 'abandn' instead of 'abandon')")
        print("  • Wrong word that happens to be in the wordlist")
        print("\n💡 Try checking each word letter-by-letter against your source")

print("\n" + "=" * 70)

