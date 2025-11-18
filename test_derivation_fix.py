#!/usr/bin/env python
"""
Test script to verify address derivation fix
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from django.conf import settings
from wallet.models import CryptoNetwork, User
from wallet.utils import create_deposit_address, derive_address_from_xpub
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("TESTING ADDRESS DERIVATION FIX")
print("=" * 60)

# Check environment variable
xpub_env = os.getenv('DEFAULT_XPUB', '')
print(f"\n1. Environment Check:")
print(f"   DEFAULT_XPUB from env: {'Set' if xpub_env else 'Not set'}")
print(f"   Length: {len(xpub_env) if xpub_env else 0}")
if xpub_env:
    print(f"   Prefix: {xpub_env[:4]}")
    print(f"   First 30 chars: {xpub_env[:30]}...")

# Check settings
xpub_settings = getattr(settings, 'DEFAULT_XPUB', '')
print(f"\n2. Settings Check:")
print(f"   DEFAULT_XPUB from settings: {'Set' if xpub_settings else 'Not set'}")
print(f"   Length: {len(xpub_settings) if xpub_settings else 0}")

# Get network
try:
    network = CryptoNetwork.objects.get(key='btc', is_active=True)
    print(f"\n3. Network Check:")
    print(f"   Network: {network.name}")
    print(f"   Key: {network.key}")
    print(f"   is_testnet: {network.is_testnet}")
    print(f"   network.xpub: {'Set' if network.xpub else 'Not set'}")
    
    # Test xpub resolution (same logic as create_deposit_address)
    xpub = network.xpub or os.getenv('DEFAULT_XPUB') or getattr(settings, 'DEFAULT_XPUB', '')
    print(f"\n4. Xpub Resolution:")
    print(f"   Resolved xpub: {'Set' if xpub else 'EMPTY!'}")
    print(f"   Length: {len(xpub) if xpub else 0}")
    if xpub:
        print(f"   Prefix: {xpub[:4]}")
        print(f"   Source: {'network.xpub' if network.xpub else ('env' if os.getenv('DEFAULT_XPUB') else 'settings')}")
    
    # Test direct derivation
    if xpub:
        print(f"\n5. Direct Derivation Test:")
        try:
            addr = derive_address_from_xpub(xpub, 0, network.key, network.is_testnet)
            print(f"   ✓ Success: {addr}")
            print(f"   Format: {'Bech32 (BIP84)' if addr.startswith('bc1') else 'Other'}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test create_deposit_address (full flow)
    if xpub:
        print(f"\n6. Full Flow Test (create_deposit_address):")
        try:
            user = User.objects.first()
            if not user:
                print("   ⚠ No users found, skipping full flow test")
            else:
                # Delete any existing deposit addresses for clean test
                from wallet.models import DepositAddress
                DepositAddress.objects.filter(user=user, network=network).delete()
                
                deposit_addr = create_deposit_address(user, network)
                print(f"   ✓ Success!")
                print(f"   Address: {deposit_addr.address}")
                print(f"   Index: {deposit_addr.index}")
                print(f"   Format: {'Bech32 (BIP84)' if deposit_addr.address.startswith('bc1') else 'Other'}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n5. Skipping tests - no xpub available")
        
except CryptoNetwork.DoesNotExist:
    print("   ✗ Bitcoin network not found in database")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

