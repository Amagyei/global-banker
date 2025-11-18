#!/usr/bin/env python
"""
Alternative: Get vpub directly from Electrum wallet file or console.
This avoids needing to type the mnemonic.
"""
import sys
import os

print("=" * 70)
print("GET VPUB FROM ELECTRUM (Alternative Method)")
print("=" * 70)
print("""
Since the mnemonic has a checksum error, let's try getting the vpub
directly from Electrum instead.

METHOD 1: Electrum Console (Easiest)
------------------------------------
1. Open Electrum wallet
2. Go to: View → Show Console (or press Ctrl+Shift+C)
3. In the console, type:

   wallet.get_master_public_key()

4. This will show all master public keys
5. Look for the one with path m/84'/1'/0' (for testnet)
6. Copy the vpub value

METHOD 2: Wallet File (If you have access)
-------------------------------------------
If you can access the Electrum wallet file, we can read it.
But this requires the wallet password.

METHOD 3: Fix Mnemonic First
----------------------------
Run: python check_mnemonic.py <your_mnemonic>
This will help identify which word has a typo.

Which method would you like to use?
""")

print("\n" + "=" * 70)
print("QUICK CHECK: Electrum Console Command")
print("=" * 70)
print("""
In Electrum console, try these commands:

# Get all master public keys
wallet.get_master_public_keys()

# Or get specific BIP84 key
wallet.get_master_public_key('p2wpkh')

# Or get by derivation path
wallet.get_master_public_key('m/84h/1h/0h')  # Testnet

Look for the output that shows:
- Path: m/84'/1'/0' or m/84h/1h/0h
- Format: vpub...
- Script type: p2wpkh
""")

