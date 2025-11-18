#!/usr/bin/env python
"""
Attempt to fix mnemonic checksum by trying variations of each word.
This is a brute-force approach that tries common typos.
"""
import sys
from difflib import get_close_matches

# Get mnemonic from command line
if len(sys.argv) < 2:
    print("Usage: python fix_checksum.py word1 word2 ... word12")
    sys.exit(1)

words = sys.argv[1:]

if len(words) not in [12, 15, 18, 21, 24]:
    print(f"❌ Invalid word count: {len(words)}")
    print("   Mnemonic must be 12, 15, 18, 21, or 24 words")
    sys.exit(1)

print("=" * 70)
print("ATTEMPTING TO FIX MNEMONIC CHECKSUM")
print("=" * 70)
print(f"\nOriginal mnemonic ({len(words)} words):")
print(" ".join(words))
print("\n" + "-" * 70)

# Load BIP39 wordlist
try:
    from bip_utils.bip.bip39 import Bip39MnemonicDecoder
    from bip_utils import Bip39Languages
    decoder = Bip39MnemonicDecoder(Bip39Languages.ENGLISH)
    wordlist_obj = decoder.m_words_list
    wordlist = []
    for i in range(wordlist_obj.Length()):
        wordlist.append(wordlist_obj.GetWordAtIdx(i))
    print(f"✅ Loaded BIP39 wordlist ({len(wordlist)} words)")
except Exception as e:
    print(f"❌ Failed to load wordlist: {e}")
    sys.exit(1)

# Try to validate current mnemonic
from bip_utils import Bip39MnemonicValidator
validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)

mnemonic = " ".join(words)
if validator.Validate(mnemonic):
    print("✅ Mnemonic is already valid!")
    print(f"\nValid mnemonic: {mnemonic}")
    sys.exit(0)

print("❌ Current mnemonic has checksum error")
print("\nTrying to fix by testing word variations...")
print("(This may take a while for 12 words)")
print("-" * 70)

# Common typo patterns
def get_variations(word):
    """Generate common typo variations of a word"""
    variations = set([word.lower()])
    
    # Try close matches from wordlist
    close = get_close_matches(word.lower(), wordlist, n=10, cutoff=0.7)
    variations.update(close)
    
    # Common single-character typos
    if len(word) > 3:
        # Try changing one character
        for i in range(len(word)):
            for char in 'abcdefghijklmnopqrstuvwxyz':
                new_word = word[:i] + char + word[i+1:]
                if new_word in wordlist:
                    variations.add(new_word)
    
    return list(variations)[:20]  # Limit to 20 variations per word

# Strategy: Try fixing one word at a time
print("\nStrategy: Testing each word position with variations...")
print("(This will test the most likely typos first)")

found_fix = False
total_tests = 0

for pos in range(len(words)):
    if found_fix:
        break
    
    word = words[pos]
    print(f"\nTesting position {pos + 1}: '{word}'")
    
    # Get variations for this word
    variations = get_variations(word)
    print(f"  Trying {len(variations)} variations...")
    
    for variant in variations:
        if variant == word.lower():
            continue  # Skip the original
        
        # Test with this variation
        test_words = words.copy()
        test_words[pos] = variant
        test_mnemonic = " ".join(test_words)
        
        total_tests += 1
        if total_tests % 100 == 0:
            print(f"  ... tested {total_tests} combinations so far...")
        
        try:
            if validator.Validate(test_mnemonic):
                print("\n" + "=" * 70)
                print("✅ FOUND VALID MNEMONIC!")
                print("=" * 70)
                print(f"\nFixed word at position {pos + 1}:")
                print(f"  Was: '{word}'")
                print(f"  Now: '{variant}'")
                print(f"\n✅ Valid mnemonic:")
                print(f"   {test_mnemonic}")
                print("\n" + "=" * 70)
                found_fix = True
                break
        except:
            pass

if not found_fix:
    print("\n" + "=" * 70)
    print("❌ Could not automatically fix the checksum")
    print("=" * 70)
    print(f"\nTested {total_tests} combinations")
    print("\n💡 The typo might be:")
    print("   • More than one character wrong")
    print("   • A completely different word")
    print("   • Words in wrong order")
    print("\n💡 Try manually checking each word against your source")
    print("   Run: python debug_mnemonic.py word1 word2 ... word12")
    print("   to see which words are suspicious")

