"""
Test BIP84 address derivation with mainnet xpub
"""
import os
from bip_utils import Bip84, Bip44Coins, Bip44Changes

xpub = os.getenv('DEFAULT_XPUB', '')
print(f'Testing BIP84 derivation...')
print(f'Xpub prefix: {xpub[:4]}')
print(f'Xpub length: {len(xpub)}')

try:
    bip84 = Bip84.FromExtendedKey(xpub, Bip44Coins.BITCOIN)
    print('✓ BIP84 created successfully')
    addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(0).PublicKey().ToAddress()
    print(f'✓ Address (index 0): {addr}')
    
    # Test a few more addresses
    for i in range(1, 5):
        addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
        print(f'✓ Address (index {i}): {addr}')
except Exception as e:
    print(f'✗ Error: {e}')
    print(f'Error type: {type(e).__name__}')
    import traceback
    traceback.print_exc()

