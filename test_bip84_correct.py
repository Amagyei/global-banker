"""
Test bip_utils BIP84 derivation with correct usage
"""
import os
from bip_utils import Bip84, Bip84Coins, Bip44Changes

xpub = os.getenv('DEFAULT_XPUB', '')
print(f'Testing bip_utils with zpub: {xpub[:20]}...')

try:
    # According to documentation, this should work
    print('\n1. Creating BIP84 from zpub...')
    bip84 = Bip84.FromExtendedKey(xpub, Bip84Coins.BITCOIN)
    print('   ✓ BIP84 object created')
    
    print('\n2. Deriving addresses...')
    for i in range(3):
        address = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
        print(f'   Address {i}: {address}')
        
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
    print('\nTrying alternative: Check if Bip84Coins enum values...')
    try:
        print(f'Bip84Coins.BITCOIN = {Bip84Coins.BITCOIN}')
        print(f'Type: {type(Bip84Coins.BITCOIN)}')
        print(f'Dir: {[x for x in dir(Bip84Coins) if not x.startswith("_")]}')
    except:
        pass

