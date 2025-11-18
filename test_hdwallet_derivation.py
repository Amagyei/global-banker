"""
Test hdwallet address derivation with mainnet xpub
"""
import os
from hdwallet import HDWallet
from hdwallet.symbols import BTC

xpub = os.getenv('DEFAULT_XPUB', '')
print(f'Testing hdwallet derivation...')
print(f'Xpub prefix: {xpub[:4]}')
print(f'Xpub length: {len(xpub)}')

try:
    hdwallet = HDWallet(symbol=BTC)
    hdwallet.from_xpublic_key(xpub)
    print('✓ HDWallet initialized successfully')
    
    # Derive addresses at m/84'/0'/0'/0/index (BIP84 native segwit for mainnet)
    for i in range(5):
        path = f"m/84'/0'/0'/0/{i}"
        hdwallet.from_path(path)
        addr = hdwallet.p2wpkh_address()  # P2WPKH for BIP84
        print(f'✓ Address (index {i}): {addr}')
except Exception as e:
    print(f'✗ Error: {e}')
    print(f'Error type: {type(e).__name__}')
    import traceback
    traceback.print_exc()

