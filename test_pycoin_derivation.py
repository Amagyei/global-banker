"""
Test pycoin BIP84 derivation step by step
"""
import os
from pycoin.key.BIP32Node import BIP32Node

xpub = os.getenv('DEFAULT_XPUB', '')
print(f'Testing pycoin with zpub: {xpub[:20]}...')
print(f'Length: {len(xpub)}')

try:
    # Try to parse the zpub
    print('\n1. Parsing zpub...')
    node = BIP32Node.from_text(xpub, netcode='BTC')
    print(f'   ✓ Parsed successfully')
    print(f'   Depth: {node.depth()}')
    print(f'   As text: {node.as_text(as_private=False)[:20]}...')
    
    # Check what level this zpub is at
    # If it's already at account level (m/84'/0'/0'), we just need /0/{index}
    # If it's at master, we need m/84'/0'/0'/0/{index}
    
    print('\n2. Testing derivation...')
    # Try deriving directly if zpub is at account level
    try:
        child = node.subkey_for_path(f"0/0")
        addr = child.segwit_address()
        print(f'   ✓ Direct derivation (assuming account level): {addr}')
    except Exception as e:
        print(f'   ✗ Direct derivation failed: {e}')
    
    # Try full path if zpub is at master level
    try:
        full_path = "84'/0'/0'/0/0"
        child = node.subkey_for_path(full_path)
        addr = child.segwit_address()
        print(f'   ✓ Full path derivation: {addr}')
    except Exception as e:
        print(f'   ✗ Full path derivation failed: {e}')
    
    # Try if zpub is already at m/84'/0'/0'
    try:
        account_path = "84'/0'/0'"
        account_node = node.subkey_for_path(account_path)
        child = account_node.subkey_for_path("0/0")
        addr = child.segwit_address()
        print(f'   ✓ Account-level derivation: {addr}')
    except Exception as e:
        print(f'   ✗ Account-level derivation failed: {e}')
        
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()

