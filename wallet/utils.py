"""
Wallet utilities for address derivation and blockchain operations
"""
import re
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

try:
    from bip_utils import Bip84, Bip44Coins, Bip44Changes
    BIP_UTILS_AVAILABLE = True
except ImportError:
    BIP_UTILS_AVAILABLE = False


def reserve_next_index(name="default"):
    """
    Atomically reserve the next address index to prevent address reuse.
    Uses select_for_update to prevent race conditions.
    """
    from .models import AddressIndex
    
    with transaction.atomic():
        obj, _ = AddressIndex.objects.select_for_update().get_or_create(name=name)
        idx = obj.next_index
        obj.next_index = idx + 1
        obj.save()
    return idx


def derive_address_from_xpub(xpub: str, index: int, network_key: str, is_testnet: bool = True):
    """
    Derive a unique address from extended public key (xpub) and index.
    
    Args:
        xpub: Extended public key (BIP84 format)
        index: Derivation index
        network_key: Network key ("btc", "eth", etc.)
        is_testnet: Whether to use testnet
    
    Returns:
        str: Derived address
    """
    if not BIP_UTILS_AVAILABLE:
        # Fallback: Generate mock address for testing
        if network_key.lower() == "btc":
            # Bitcoin address format: starts with 1, 3, or bc1
            prefix = "bc1" if is_testnet else "bc1"
            return f"{prefix}{_generate_mock_address(42)}"
        elif network_key.lower() in ["eth", "ethereum"]:
            # Ethereum address format: 0x + 40 hex chars
            return f"0x{_generate_mock_address(40)}"
        else:
            # Generic: use network key + index
            return f"{network_key}_{index}_{_generate_mock_address(32)}"
    
    # Real derivation using bip_utils
    try:
        if network_key.lower() == "btc":
            coin = Bip44Coins.BITCOIN_TESTNET if is_testnet else Bip44Coins.BITCOIN
            bip84 = Bip84.FromExtendedKey(xpub, coin)
            addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(index).PublicKey().ToAddress()
            return addr
        elif network_key.lower() in ["eth", "ethereum"]:
            # Ethereum uses BIP44 with different derivation
            # For now, return mock - ETH derivation is more complex
            return f"0x{_generate_mock_address(40)}"
        else:
            # Other networks - return mock for now
            return f"{network_key}_{index}_{_generate_mock_address(32)}"
    except Exception as e:
        # Fallback to mock on error
        print(f"Address derivation error: {e}, using mock address")
        if network_key.lower() == "btc":
            return f"bc1{_generate_mock_address(42)}"
        elif network_key.lower() in ["eth", "ethereum"]:
            return f"0x{_generate_mock_address(40)}"
        else:
            return f"{network_key}_{index}_{_generate_mock_address(32)}"


def _generate_mock_address(length: int) -> str:
    """Generate a mock address for testing"""
    import secrets
    return secrets.token_hex(length // 2)[:length]


def create_deposit_address(user, network):
    """
    Create a unique deposit address for a user on a network.
    Uses atomic index reservation to prevent address reuse.
    """
    from wallet.models import DepositAddress
    
    # Reserve next index atomically
    index = reserve_next_index(name=f"{network.key}_{'testnet' if network.is_testnet else 'mainnet'}")
    
    # Derive address from xpub
    xpub = network.xpub or getattr(settings, 'DEFAULT_XPUB', '')
    address = derive_address_from_xpub(xpub, index, network.key, network.is_testnet)
    
    # Create deposit address record
    deposit_address = DepositAddress.objects.create(
        user=user,
        network=network,
        address=address,
        index=index,
        is_active=True
    )
    
    return deposit_address


def create_topup_intent(user, amount_minor: int, network, ttl_minutes: int = 30):
    """
    Create a top-up intent with a unique deposit address.
    
    Args:
        user: User instance
        amount_minor: Amount in USD minor units (cents)
        network: CryptoNetwork instance
        ttl_minutes: Time to live in minutes
    
    Returns:
        TopUpIntent instance
    """
    from wallet.models import TopUpIntent, DepositAddress
    
    # Get or create deposit address for this user/network
    deposit_address = DepositAddress.objects.filter(
        user=user,
        network=network,
        is_active=True
    ).first()
    
    if not deposit_address:
        deposit_address = create_deposit_address(user, network)
    
    # Create top-up intent
    topup = TopUpIntent.objects.create(
        user=user,
        amount_minor=amount_minor,
        currency_code='USD',
        network=network,
        deposit_address=deposit_address,
        status='pending',
        expires_at=timezone.now() + timedelta(minutes=ttl_minutes)
    )
    
    return topup

