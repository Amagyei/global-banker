#!/usr/bin/env python3
"""
Check the current DEFAULT_XPUB format and provide guidance.
For testnet, you need a tpub key (not vpub).
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from django.conf import settings

def main():
    # Get xpub from various sources
    xpub = None
    sources = []
    
    # Try environment variable
    xpub = os.environ.get('DEFAULT_XPUB', '')
    if xpub:
        sources.append('environment variable')
    
    # Try settings
    if not xpub:
        xpub = getattr(settings, 'DEFAULT_XPUB', '')
        if xpub:
            sources.append('Django settings')
    
    # Try .env file directly
    if not xpub:
        try:
            from pathlib import Path
            env_path = Path(settings.BASE_DIR) / '.env'
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('DEFAULT_XPUB='):
                            value = line.split('=', 1)[1].strip()
                            # Remove quotes
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            if value:
                                xpub = value
                                sources.append('.env file')
                                break
        except Exception as e:
            print(f"Error reading .env: {e}")
    
    if not xpub:
        print("❌ ERROR: DEFAULT_XPUB not found in any source")
        print("\nPlease set DEFAULT_XPUB in your .env file:")
        print("  DEFAULT_XPUB=your_tpub_key_here")
        return 1
    
    print(f"✓ Found DEFAULT_XPUB (from {', '.join(sources)})")
    print(f"  Length: {len(xpub)} characters")
    print(f"  Prefix: {xpub[:4]}")
    print()
    
    # Check format
    prefix = xpub[:4].lower()
    
    if prefix == 'tpub':
        print("✅ PERFECT: You have a tpub key - this is correct for testnet!")
        print("   The system will use it directly without conversion.")
        return 0
    elif prefix == 'vpub':
        print("⚠️  WARNING: You have a vpub key, but testnet requires tpub.")
        print()
        print("Options:")
        print("  1. Export a tpub from your wallet (recommended)")
        print("  2. The system will attempt to convert vpub->tpub automatically")
        print()
        print("To export tpub from Electrum:")
        print("  - Open Electrum")
        print("  - Go to Wallet > Information")
        print("  - Look for 'Master Public Key' (should start with tpub)")
        print("  - Or use: m/44'/1'/0' derivation path for BIP44 testnet")
        print()
        
        # Try conversion
        try:
            import base58
            decoded = base58.b58decode_check(xpub)
            version_bytes = decoded[:4]
            
            if version_bytes == b'\x04\x5f\x1c\xf6':  # vpub BIP84 testnet
                new_version = b'\x04\x35\x87\xcf'  # tpub BIP44 testnet
                new_decoded = new_version + decoded[4:]
                tpub_bytes = base58.b58encode_check(new_decoded)
                tpub = tpub_bytes.decode('ascii') if isinstance(tpub_bytes, bytes) else str(tpub_bytes)
                
                print("✅ Conversion test successful!")
                print(f"   Your tpub would be: {tpub}")
                print()
                print("   You can update your .env file with:")
                print(f"   DEFAULT_XPUB={tpub}")
                return 0
            else:
                print(f"❌ Unexpected version bytes: {version_bytes.hex()}")
                return 1
        except Exception as e:
            print(f"❌ Conversion test failed: {e}")
            print("   Please export a tpub directly from your wallet.")
            return 1
    elif prefix in ['xpub', 'zpub']:
        print("❌ ERROR: You have a mainnet key (xpub/zpub), but testnet is enabled.")
        print("   Please provide a tpub key for testnet.")
        return 1
    else:
        print(f"❌ ERROR: Unknown key format: {prefix}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

