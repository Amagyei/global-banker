#!/usr/bin/env python
"""
Fix network configuration to use testnet for Bitcoin when vpub is used.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import CryptoNetwork
import os

print("=" * 70)
print("FIXING NETWORK CONFIGURATION")
print("=" * 70)

# Check DEFAULT_XPUB
xpub = os.environ.get('DEFAULT_XPUB', '')
if xpub.startswith('vpub'):
    print("\n✅ DEFAULT_XPUB is testnet (vpub)")
    should_be_testnet = True
elif xpub.startswith('zpub'):
    print("\n✅ DEFAULT_XPUB is mainnet (zpub)")
    should_be_testnet = False
else:
    print(f"\n⚠️  DEFAULT_XPUB format unclear: {xpub[:10]}...")
    should_be_testnet = True  # Default to testnet for safety

# Get Bitcoin network
btc_network = CryptoNetwork.objects.filter(key='btc').first()

if btc_network:
    print(f"\nCurrent Bitcoin network config:")
    print(f"  Name: {btc_network.name}")
    print(f"  is_testnet: {btc_network.is_testnet}")
    print(f"  API: {btc_network.explorer_api_url}")
    
    if btc_network.is_testnet != should_be_testnet:
        print(f"\n⚠️  MISMATCH: Network is {'testnet' if btc_network.is_testnet else 'mainnet'}")
        print(f"   but vpub indicates {'testnet' if should_be_testnet else 'mainnet'}")
        
        response = input(f"\nFix network to {'testnet' if should_be_testnet else 'mainnet'}? (y/n): ")
        if response.lower() == 'y':
            btc_network.is_testnet = should_be_testnet
            if should_be_testnet:
                btc_network.explorer_api_url = 'https://blockstream.info/testnet/api'
                btc_network.explorer_url = 'https://blockstream.info/testnet'
            else:
                btc_network.explorer_api_url = 'https://blockstream.info/api'
                btc_network.explorer_url = 'https://blockstream.info'
            btc_network.save()
            print(f"✅ Updated network to {'testnet' if should_be_testnet else 'mainnet'}")
        else:
            print("❌ Not updated")
    else:
        print(f"\n✅ Network configuration is correct")
else:
    print("\n❌ Bitcoin network not found in database")

print("\n" + "=" * 70)
print("💡 Next steps:")
print("   1. Verify transactions were sent to testnet addresses")
print("   2. Check addresses on: https://blockstream.info/testnet/")
print("   3. Run: python manage.py monitor_deposits")

