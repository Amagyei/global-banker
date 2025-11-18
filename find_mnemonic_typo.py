#!/usr/bin/env python
"""
Help identify which word in the mnemonic has a typo by checking each word
and suggesting corrections.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

# Get mnemonic from env or command line
mnemonic = os.environ.get('MNEMONIC', '').strip()
if mnemonic.startswith('MNEMONIC='):
    mnemonic = mnemonic.split('=', 1)[1].strip().strip('"').strip("'")

if len(sys.argv) > 1:
    mnemonic = ' '.join(sys.argv[1:])

if not mnemonic:
    print("Usage: python find_mnemonic_typo.py <word1> <word2> ... <word12>")
    print("   Or set MNEMONIC in .env file")
    print("   Or: MNEMONIC='word1 word2...' python find_mnemonic_typo.py")
    sys.exit(1)

words = mnemonic.split()
print("=" * 70)
print("FINDING MNEMONIC TYPO")
print("=" * 70)
print(f"\nMnemonic: {len(words)} words")
print(f"Words: {' '.join(words)}")

# Load BIP39 wordlist
from bip_utils.bip.bip39.bip39_wordlist import Bip39WordList
from bip_utils import Bip39Languages
from difflib import get_close_matches

wordlist = Bip39WordList(Bip39Languages.ENGLISH).GetWordList()
print(f"\nBIP39 wordlist loaded ({len(wordlist)} words)")

# Check each word
print("\n" + "-" * 70)
print("Checking each word...")
print("-" * 70)

invalid_words = []
for i, word in enumerate(words, 1):
    word_lower = word.lower().strip()
    if word_lower not in wordlist:
        invalid_words.append((i, word))
        suggestions = get_close_matches(word_lower, wordlist, n=5, cutoff=0.5)
        print(f"❌ Word {i:2d}: '{word}' - NOT in BIP39 wordlist")
        if suggestions:
            print(f"   → Suggestions: {', '.join(suggestions)}")
    else:
        print(f"✅ Word {i:2d}: '{word}'")

if invalid_words:
    print("\n" + "=" * 70)
    print(f"❌ FOUND {len(invalid_words)} INVALID WORD(S)")
    print("=" * 70)
    print("\nFix these words in your mnemonic:")
    for pos, word in invalid_words:
        suggestions = get_close_matches(word.lower(), wordlist, n=5, cutoff=0.5)
        print(f"\n  Position {pos}: '{word}'")
        if suggestions:
            print(f"    Try: {', '.join(suggestions)}")
        else:
            print(f"    No close matches found - check spelling carefully")
else:
    print("\n" + "=" * 70)
    print("✅ ALL WORDS ARE VALID BIP39 WORDS")
    print("=" * 70)
    print("\nBut checksum is still failing. This means:")
    print("  • One word might be a very close typo (e.g., 'abandn' vs 'abandon')")
    print("  • Words might be in wrong order")
    print("  • Missing or extra word")
    print("\n💡 Try checking each word letter by letter against the BIP39 wordlist")
    print("   Full wordlist: https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt")

print("\n" + "=" * 70)

