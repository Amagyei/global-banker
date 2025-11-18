#!/usr/bin/env python
"""
Tool to help fix mnemonic checksum errors by identifying problematic words.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

# Get mnemonic
mnemonic = os.environ.get('MNEMONIC', '').strip()
if mnemonic.startswith('MNEMONIC='):
    mnemonic = mnemonic.split('=', 1)[1].strip().strip('"').strip("'")

if not mnemonic:
    print("❌ No MNEMONIC found in .env")
    print("   Make sure .env has: MNEMONIC=word1 word2 word3 ... word12")
    sys.exit(1)

words = mnemonic.split()
print("=" * 70)
print("MNEMONIC CHECKSUM FIXER")
print("=" * 70)
print(f"\nMnemonic has {len(words)} words")
print(f"Words: {' '.join(words[:6])}... {' '.join(words[-6:])}")

# Check each word
print(f"\nChecking each word...")
from bip_utils.bip.bip39.bip39_wordlist import Bip39WordList
from bip_utils import Bip39Languages
from difflib import get_close_matches

wordlist = Bip39WordList(Bip39Languages.ENGLISH).GetWordList()
invalid_words = []
suspicious_words = []

for i, word in enumerate(words, 1):
    word_lower = word.lower().strip()
    if word_lower not in wordlist:
        invalid_words.append((i, word))
        suggestions = get_close_matches(word_lower, wordlist, n=5, cutoff=0.5)
        print(f"  ❌ Word {i}: '{word}' - NOT in BIP39 wordlist")
        if suggestions:
            print(f"      → Try: {', '.join(suggestions)}")
    else:
        # Check for common typos even if word is in list
        close_matches = get_close_matches(word_lower, wordlist, n=3, cutoff=0.8)
        if len(close_matches) > 1:  # More than just itself
            suspicious_words.append((i, word, close_matches))
        print(f"  ✅ Word {i}: '{word}'")

if invalid_words:
    print(f"\n❌ Found {len(invalid_words)} word(s) NOT in BIP39 wordlist:")
    for pos, word in invalid_words:
        suggestions = get_close_matches(word.lower(), wordlist, n=5, cutoff=0.5)
        print(f"   Position {pos}: '{word}'")
        if suggestions:
            print(f"      Possible corrections: {', '.join(suggestions)}")
    
    print(f"\n💡 Fix these words in your .env file and try again")
elif suspicious_words:
    print(f"\n⚠️  Found {len(suspicious_words)} word(s) that might be typos:")
    for pos, word, matches in suspicious_words:
        other_matches = [m for m in matches if m != word.lower()]
        if other_matches:
            print(f"   Position {pos}: '{word}' - similar to: {', '.join(other_matches)}")
else:
    print(f"\n✅ All words are valid BIP39 words")
    print(f"\n⚠️  But checksum is failing. This could mean:")
    print(f"   • Words are in wrong order")
    print(f"   • One word is a very close typo (e.g., 'abandn' vs 'abandon')")
    print(f"   • Missing or extra word")
    print(f"\n💡 Try:")
    print(f"   1. Double-check each word letter by letter")
    print(f"   2. Make sure words are in the correct order")
    print(f"   3. Verify you have exactly 12 or 24 words")

print("\n" + "=" * 70)

