#!/usr/bin/env python
"""
Verify that generated addresses match the vpub derivation.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import DepositAddress
from wallet.utils import derive_address_from_xpub
import os

print("=" * 70)
print("ADDRESS VERIFICATION")
print("=" * 70)

# Get DEFAULT_XPUB
xpub = os.environ.get('DEFAULT_XPUB', '')
if not xpub:
    from django.conf import settings
    xpub = getattr(settings, 'DEFAULT_XPUB', '')

if not xpub:
    print("\n❌ DEFAULT_XPUB not found in environment or settings")
    sys.exit(1)

print(f"\nUsing xpub: {xpub[:30]}... (length: {len(xpub)})")

# Get all deposit addresses
addresses = DepositAddress.objects.filter(is_active=True).select_related('network')

print(f"\nVerifying {addresses.count()} address(es):\n")

for addr in addresses:
    print(f"Address: {addr.address}")
    print(f"  Index: {addr.index}")
    print(f"  Network: {addr.network.name} (testnet={addr.network.is_testnet})")
    
    # Try to re-derive the address
    try:
        derived = derive_address_from_xpub(
            xpub, 
            addr.index, 
            addr.network.key, 
            addr.network.is_testnet
        )
        
        if derived == addr.address:
            print(f"  ✅ Address matches derivation")
        else:
            print(f"  ❌ MISMATCH!")
            print(f"     Expected: {addr.address}")
            print(f"     Derived:  {derived}")
    except Exception as e:
        print(f"  ❌ Error deriving address: {e}")
    
    print()

print("=" * 70)
print("💡 If addresses don't match:")
print("   • The vpub might be wrong")
print("   • The derivation path might be incorrect")
print("   • The index might be off")
print("\n💡 If addresses match but no transactions:")
print("   • Verify transactions were actually sent")
print("   • Check the correct network (testnet/mainnet)")
print("   • Verify the transaction was broadcast")

