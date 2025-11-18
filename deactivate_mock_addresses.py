#!/usr/bin/env python
"""
Deactivate mock deposit addresses in the database.
Mock addresses are identified by:
- Starting with bc1, tb1, or 0x
- Being exactly 45 chars (bc1/tb1) or 42 chars (0x) with all hex
- Not being valid bech32 encoded addresses
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import DepositAddress
import re

def is_mock_address(address: str) -> bool:
    """Check if an address is a mock address"""
    if not address:
        return False
    
    # Mock Bitcoin mainnet: bc1 + 42 hex chars = 45 chars
    if address.startswith('bc1') and len(address) == 45:
        # Check if it's all hex after bc1
        hex_part = address[3:]
        if all(c in '0123456789abcdef' for c in hex_part.lower()):
            return True
    
    # Mock Bitcoin testnet: tb1 + 42 hex chars = 45 chars
    if address.startswith('tb1') and len(address) == 45:
        hex_part = address[3:]
        if all(c in '0123456789abcdef' for c in hex_part.lower()):
            return True
    
    # Mock Ethereum: 0x + 40 hex chars = 42 chars
    if address.startswith('0x') and len(address) == 42:
        hex_part = address[2:]
        if all(c in '0123456789abcdef' for c in hex_part.lower()):
            return True
    
    return False

# Find all mock addresses
mock_addresses = DepositAddress.objects.filter(is_active=True)
mock_count = 0
deactivated = []

for addr in mock_addresses:
    if is_mock_address(addr.address):
        mock_count += 1
        deactivated.append({
            'id': addr.id,
            'address': addr.address,
            'network': addr.network.key,
            'user': addr.user.email if addr.user else 'Unknown'
        })
        addr.is_active = False
        addr.save()

print("=" * 70)
print("MOCK ADDRESS DEACTIVATION")
print("=" * 70)
print(f"\nFound {mock_count} mock addresses")
print(f"Deactivated {len(deactivated)} addresses\n")

if deactivated:
    print("Deactivated addresses:")
    for item in deactivated:
        print(f"  • {item['address']} (Network: {item['network']}, User: {item['user']})")
    print(f"\n✅ All mock addresses have been deactivated")
    print(f"\n💡 Next steps:")
    print(f"   1. Ensure DEFAULT_XPUB is set in .env")
    print(f"   2. Create new top-up intents to get real derived addresses")
else:
    print("✅ No mock addresses found")

