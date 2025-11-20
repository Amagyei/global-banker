#!/usr/bin/env python3
"""
Script to create a hot wallet for a network.
This derives a hot wallet address and encrypted xprv from the master xprv.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import HotWallet, CryptoNetwork
from wallet.private_key_manager import PrivateKeyManager
from wallet.utils import derive_address_from_xpub
from django.conf import settings


def create_hot_wallet(network_key='btc', derivation_path=None):
    """
    Create a hot wallet for the specified network.
    
    Args:
        network_key: Network key (e.g., 'btc')
        derivation_path: Custom derivation path (e.g., "m/84'/1'/1'"). 
                         If None, uses default: "m/84'/1'/1'" for testnet or "m/84'/0'/1'" for mainnet
    """
    # Get network
    try:
        network = CryptoNetwork.objects.get(key=network_key, is_active=True)
    except CryptoNetwork.DoesNotExist:
        print(f"❌ Network {network_key} not found or not active")
        return None
    
    # Check if hot wallet already exists
    existing = HotWallet.objects.filter(network=network, is_active=True).first()
    if existing:
        print(f"⚠️  Hot wallet already exists for {network.name}:")
        print(f"   Address: {existing.address}")
        print(f"   Created: {existing.created_at}")
        response = input("   Create new one anyway? (y/N): ")
        if response.lower() != 'y':
            return existing
    
    # Get master xprv
    master_xprv = os.getenv('MASTER_XPRV')
    if not master_xprv:
        master_xprv = getattr(settings, 'MASTER_XPRV', '')
    
    if not master_xprv:
        print("❌ MASTER_XPRV not set in environment or settings")
        print("   Set it with: export MASTER_XPRV='your_xprv_here'")
        return None
    
    # Get master xpub for address derivation
    master_xpub = os.getenv('DEFAULT_XPUB')
    if not master_xpub:
        master_xpub = getattr(settings, 'DEFAULT_XPUB', '')
    
    if not master_xpub:
        print("❌ DEFAULT_XPUB not set in environment or settings")
        return None
    
    # Set default derivation path if not provided
    is_testnet = network.effective_is_testnet
    if derivation_path is None:
        # Hot wallet uses account index 1 (user wallets use 0)
        coin_type = 1 if is_testnet else 0
        derivation_path = f"m/84'/{coin_type}'/1'"
    
    print(f"\n📝 Creating hot wallet for {network.name} ({'testnet' if is_testnet else 'mainnet'})...")
    print(f"   Derivation path: {derivation_path}")
    
    # Derive hot wallet address from xpub
    # For hot wallet, we use index 0 at the address level (m/84'/1'/1'/0/0)
    try:
        hot_wallet_address = derive_address_from_xpub(
            master_xpub,
            index=0,  # First address for hot wallet
            network_key=network.key,
            is_testnet=is_testnet
        )
        print(f"   ✓ Derived address: {hot_wallet_address}")
    except Exception as e:
        print(f"❌ Failed to derive address: {e}")
        return None
    
    # Encrypt master xprv (for hot wallet, we'll store the master xprv encrypted)
    # In production, you might want to derive a separate xprv for the hot wallet
    key_manager = PrivateKeyManager()
    try:
        encrypted_xprv = key_manager.encrypt_xprv(master_xprv)
        print(f"   ✓ Encrypted xprv")
    except Exception as e:
        print(f"❌ Failed to encrypt xprv: {e}")
        return None
    
    # Create hot wallet record
    try:
        hot_wallet = HotWallet.objects.create(
            network=network,
            address=hot_wallet_address,
            encrypted_xprv=encrypted_xprv,
            derivation_path=derivation_path,
            balance_atomic=0,
            is_active=True
        )
        print(f"\n✅ Hot wallet created successfully!")
        print(f"   ID: {hot_wallet.id}")
        print(f"   Address: {hot_wallet.address}")
        print(f"   Network: {network.name}")
        print(f"   Status: {'Active' if hot_wallet.is_active else 'Inactive'}")
        return hot_wallet
    except Exception as e:
        print(f"❌ Failed to create hot wallet: {e}")
        return None


def create_cold_wallet(network_key='btc', address=None, name='Main Reserve'):
    """
    Create a cold wallet record (address only, no private key).
    
    Args:
        network_key: Network key (e.g., 'btc')
        address: Cold wallet address (if None, prompts for input)
        name: Name for the cold wallet
    """
    # Get network
    try:
        network = CryptoNetwork.objects.get(key=network_key, is_active=True)
    except CryptoNetwork.DoesNotExist:
        print(f"❌ Network {network_key} not found or not active")
        return None
    
    # Check if cold wallet already exists
    existing = ColdWallet.objects.filter(network=network, is_active=True, name=name).first()
    if existing:
        print(f"⚠️  Cold wallet '{name}' already exists for {network.name}:")
        print(f"   Address: {existing.address}")
        response = input("   Create new one anyway? (y/N): ")
        if response.lower() != 'y':
            return existing
    
    # Get address if not provided
    if not address:
        address = input(f"Enter cold wallet address for {network.name}: ").strip()
        if not address:
            print("❌ Address is required")
            return None
    
    # Validate address format (basic check)
    if network.key.lower() == 'btc':
        if network.effective_is_testnet:
            if not (address.startswith('tb1') or address.startswith('m') or address.startswith('n') or address.startswith('2')):
                print(f"⚠️  Warning: Address doesn't look like a testnet address")
        else:
            if not (address.startswith('bc1') or address.startswith('1') or address.startswith('3')):
                print(f"⚠️  Warning: Address doesn't look like a mainnet address")
    
    # Create cold wallet record
    try:
        from wallet.models import ColdWallet
        cold_wallet = ColdWallet.objects.create(
            network=network,
            address=address,
            name=name,
            is_active=True
        )
        print(f"\n✅ Cold wallet created successfully!")
        print(f"   ID: {cold_wallet.id}")
        print(f"   Name: {cold_wallet.name}")
        print(f"   Address: {cold_wallet.address}")
        print(f"   Network: {network.name}")
        return cold_wallet
    except Exception as e:
        print(f"❌ Failed to create cold wallet: {e}")
        return None


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Create hot or cold wallet')
    parser.add_argument('type', choices=['hot', 'cold'], help='Wallet type')
    parser.add_argument('--network', default='btc', help='Network key (default: btc)')
    parser.add_argument('--address', help='Cold wallet address (for cold wallet only)')
    parser.add_argument('--name', default='Main Reserve', help='Cold wallet name (default: Main Reserve)')
    parser.add_argument('--derivation-path', help='Custom derivation path for hot wallet')
    
    args = parser.parse_args()
    
    if args.type == 'hot':
        create_hot_wallet(network_key=args.network, derivation_path=args.derivation_path)
    else:
        create_cold_wallet(network_key=args.network, address=args.address, name=args.name)

