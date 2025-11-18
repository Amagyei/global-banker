"""
Wallet utilities for address derivation and blockchain operations
"""
import re
import logging
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Use bip_utils for BIP84 derivation (primary) - requires zpub to xpub conversion
try:
    from bip_utils import Bip84, Bip84Coins, Bip44Changes
    BIP_UTILS_AVAILABLE = True
except ImportError:
    BIP_UTILS_AVAILABLE = False

# Use hdwallet as fallback
try:
    from hdwallet import HDWallet
    from hdwallet.cryptocurrencies import Bitcoin
    HDWALLET_AVAILABLE = True
except ImportError:
    HDWALLET_AVAILABLE = False

# Use pycoin as additional fallback for vpub/zpub
try:
    from pycoin.symbols.btc import network as btc_mainnet
    # Try importing testnet network (may not be available in all pycoin versions)
    try:
        from pycoin.symbols.tbtc import network as btc_testnet
    except ImportError:
        # Fallback: use mainnet network with testnet flag
        btc_testnet = None
    PYCOIN_AVAILABLE = True
except ImportError:
    PYCOIN_AVAILABLE = False
    btc_mainnet = None
    btc_testnet = None

# base58 for zpub to xpub conversion
try:
    import base58
    BASE58_AVAILABLE = True
except ImportError:
    BASE58_AVAILABLE = False
    base58 = None


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


def zpub_to_xpub(zpub: str) -> str:
    """
    Convert zpub (BIP84) to xpub format for compatibility with libraries.
    This is done by changing the version bytes in the base58-encoded key.
    
    Args:
        zpub: Extended public key in zpub format (BIP84 mainnet)
    
    Returns:
        str: Extended public key in xpub format (compatible with bip_utils)
    """
    if not base58:
        raise ImportError("base58 library required for zpub conversion")
    
    try:
        # Validate input
        if not zpub or not isinstance(zpub, str):
            raise ValueError("zpub must be a non-empty string")
        
        # Use base58 check decode (includes checksum validation)
        # This should return bytes
        decoded = base58.b58decode_check(zpub)
        
        if not isinstance(decoded, bytes):
            raise ValueError(f"Expected bytes from b58decode_check, got {type(decoded)}")
        
        # zpub version bytes: 0x04b24746 (mainnet BIP84) or 0x045f1cf6 (testnet BIP84)
        # xpub version bytes: 0x0488b21e (mainnet BIP44) or 0x043587cf (testnet BIP44)
        # Check first 4 bytes to determine network
        if len(decoded) < 4:
            raise ValueError(f"Decoded zpub too short: {len(decoded)} bytes")
        
        version_bytes = decoded[:4]
        
        if version_bytes == b'\x04\xb2\x47\x46':  # zpub mainnet BIP84
            new_version = b'\x04\x88\xb2\x1e'  # xpub mainnet (for bip_utils compatibility)
        elif version_bytes == b'\x04\x5f\x1c\xf6':  # zpub testnet BIP84
            new_version = b'\x04\x35\x87\xcf'  # xpub testnet
        else:
            # Unknown format, assume mainnet
            logger.warning(f"Unknown zpub version bytes: {version_bytes.hex()}, assuming mainnet")
            new_version = b'\x04\x88\xb2\x1e'
        
        # Replace version bytes (keep the rest of the key data)
        new_decoded = new_version + decoded[4:]
        
        # Re-encode with checksum using base58 check encode
        xpub_bytes = base58.b58encode_check(new_decoded)
        
        # base58.b58encode_check returns bytes - decode to string
        if isinstance(xpub_bytes, bytes):
            xpub = xpub_bytes.decode('ascii')  # base58 is ASCII-only
        else:
            # If it's already a string (shouldn't happen), use it
            xpub = str(xpub_bytes)
        
        return xpub
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error in zpub conversion: {e}")
        # Try to get more info
        try:
            decoded = base58.b58decode_check(zpub)
            logger.debug(f"Decoded length: {len(decoded)}, first 10 bytes: {decoded[:10].hex()}")
        except:
            pass
        raise ValueError(f"Invalid zpub format - encoding issue: {e}")
    except Exception as e:
        logger.error(f"Failed to convert zpub to xpub: {e}")
        raise ValueError(f"Invalid zpub format: {e}")


def vpub_to_tpub(vpub: str) -> str:
    """
    Convert vpub (BIP84 testnet) to tpub format for compatibility with libraries.
    This is done by changing the version bytes in the base58-encoded key.
    
    Args:
        vpub: Extended public key in vpub format (BIP84 testnet)
    
    Returns:
        str: Extended public key in tpub format
    """
    if not BASE58_AVAILABLE:
        raise ImportError("base58 library required for vpub conversion")
    
    try:
        # Decode vpub
        decoded = base58.b58decode_check(vpub)
        
        if len(decoded) < 4:
            raise ValueError(f"Decoded vpub too short: {len(decoded)} bytes")
        
        version_bytes = decoded[:4]
        
        # vpub version: 0x045f1cf6 (BIP84 testnet)
        # tpub version: 0x043587cf (BIP44/BIP32 testnet)
        if version_bytes == b'\x04\x5f\x1c\xf6':  # vpub
            new_version = b'\x04\x35\x87\xcf'  # tpub
        else:
            logger.warning(f"Unexpected vpub version bytes: {version_bytes.hex()}")
            new_version = b'\x04\x35\x87\xcf'
        
        # Replace version bytes
        new_decoded = new_version + decoded[4:]
        
        # Re-encode with checksum
        tpub_bytes = base58.b58encode_check(new_decoded)
        
        if isinstance(tpub_bytes, bytes):
            tpub = tpub_bytes.decode('ascii')
        else:
            tpub = str(tpub_bytes)
        
        logger.info(f"Converted vpub to tpub: {vpub[:10]}... -> {tpub[:10]}...")
        return tpub
    except Exception as e:
        logger.error(f"Failed to convert vpub to tpub: {e}")
        raise ValueError(f"Invalid vpub format: {e}")


def derive_address_from_xpub(xpub: str, index: int, network_key: str, is_testnet: bool = True):
    """
    Derive a unique address from extended public key (xpub) and index.
    Handles depth 1 vpub (m/0') with BIP32 p2wpkh derivation.
    
    Args:
        xpub: Extended public key (zpub, xpub, vpub, or tpub format)
        index: Derivation index
        network_key: Network key ("btc", "eth", etc.)
        is_testnet: Whether to use testnet
    
    Returns:
        str: Derived address
    """
    if not HDWALLET_AVAILABLE and not BIP_UTILS_AVAILABLE and not PYCOIN_AVAILABLE:
        raise ImportError("At least one library (hdwallet, bip_utils, or pycoin) must be installed")
    
    try:
        # Normalize network key - handle both "btc" and "btc_testnet"
        normalized_key = network_key.lower().replace("_testnet", "").replace("_mainnet", "")
        
        if normalized_key == "btc":
            xpub_prefix = xpub[:4].lower()
            
            # Determine network based on xpub format (primary) and is_testnet parameter (secondary)
            # This allows flexibility while validating against key format
            if xpub_prefix in ['zpub', 'xpub']:
                detected_testnet = False
            elif xpub_prefix in ['vpub', 'tpub']:
                detected_testnet = True
            else:
                # Unknown format - use parameter
                detected_testnet = is_testnet
            
            # Use the is_testnet parameter as the source of truth
            # but warn if it conflicts with the key format
            actual_testnet = is_testnet
            
            if detected_testnet != is_testnet:
                logger.warning(
                    f"xpub format ({xpub_prefix}) indicates {'testnet' if detected_testnet else 'mainnet'}, "
                    f"but is_testnet parameter is {is_testnet}. Using is_testnet={is_testnet} as requested."
                )
            
            # Convert vpub to tpub for better library compatibility
            working_key = xpub
            if xpub_prefix == 'vpub' and BASE58_AVAILABLE:
                try:
                    working_key = vpub_to_tpub(xpub)
                    logger.info("Converted vpub to tpub for derivation")
                except Exception as e:
                    logger.warning(f"Could not convert vpub to tpub: {e}, will try with original")
                    working_key = xpub
            
            # Method 1: Try hdwallet with BIP32 (most reliable for depth 1)
            if HDWALLET_AVAILABLE:
                try:
                    from hdwallet import HDWallet
                    from hdwallet.cryptocurrencies import Bitcoin as BitcoinCrypto
                    
                    network_str = 'testnet' if actual_testnet else 'mainnet'
                    
                    # Try BIP32HD if available
                    try:
                        from hdwallet.hds import BIP32HD
                        hdwallet = HDWallet(cryptocurrency=BitcoinCrypto, hd=BIP32HD, network=network_str)
                        logger.info("Using hdwallet with BIP32HD")
                    except ImportError:
                        # Fallback to default (BIP44)
                        hdwallet = HDWallet(cryptocurrency=BitcoinCrypto, network=network_str)
                        logger.info("Using hdwallet with default HD")
                    
                    # Load the key
                    hdwallet.from_xpublic_key(working_key, strict=False)
                    logger.info(f"Loaded key with hdwallet")
                    
                    # Clean from_path if it exists, otherwise derive manually
                    try:
                        # Try to derive using path (external chain / address index)
                        hdwallet.clean_derivation()
                        
                        # Derive external chain (0) and address index
                        for i in [0, index]:
                            hdwallet.from_index(i, hardened=False)
                        
                        addr = hdwallet.p2wpkh_address()
                        logger.info(f"Successfully derived p2wpkh address using hdwallet at index {index}: {addr}")
                        return addr
                        
                    except AttributeError:
                        # If clean_derivation doesn't exist, try alternative approach
                        logger.info("hdwallet doesn't have clean_derivation, trying alternative")
                        
                        # Create fresh instance and derive in one go
                        hdwallet2 = HDWallet(cryptocurrency=BitcoinCrypto, network=network_str)
                        hdwallet2.from_xpublic_key(working_key, strict=False)
                        
                        # Derive using from_index
                        hdwallet2.from_index(0, hardened=False)  # External chain
                        hdwallet2.from_index(index, hardened=False)  # Address index
                        
                        addr = hdwallet2.p2wpkh_address()
                        logger.info(f"Successfully derived p2wpkh address using hdwallet (alt method) at index {index}: {addr}")
                        return addr
                        
                except Exception as hdwallet_error:
                    logger.warning(f"hdwallet derivation failed: {hdwallet_error}, trying bip_utils")
            
            # Method 2: Try bip_utils with raw BIP32
            if BIP_UTILS_AVAILABLE:
                try:
                    from bip_utils import Bip32Slip10Secp256k1
                    import hashlib
                    
                    # Use raw BIP32 to avoid depth restrictions
                    bip32_ctx = Bip32Slip10Secp256k1.FromExtendedKey(working_key)
                    
                    logger.info(f"Loaded key with bip_utils BIP32, depth: {bip32_ctx.Depth()}")
                    
                    # Derive: 0 (external chain) -> index (address)
                    external_chain = bip32_ctx.ChildKey(0)  # Non-hardened
                    address_key = external_chain.ChildKey(index)  # Non-hardened
                    
                    # Get the public key
                    pubkey = address_key.PublicKey().RawCompressed().ToHex()
                    
                    # Manual bech32 encoding
                    from bip_utils import Bech32Encoder
                    
                    # Hash160 of public key
                    sha256_hash = hashlib.sha256(bytes.fromhex(pubkey)).digest()
                    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
                    
                    # Encode as bech32 with witness version 0
                    hrp = "tb" if actual_testnet else "bc"
                    addr = Bech32Encoder.EncodeAddr(hrp, 0, ripemd160_hash)
                    
                    logger.info(f"Successfully derived p2wpkh address using bip_utils BIP32 at index {index}: {addr}")
                    return addr
                    
                except Exception as bip32_error:
                    logger.warning(f"bip_utils BIP32 derivation failed: {bip32_error}, trying pycoin")
            
            # Method 3: Try pycoin
            if PYCOIN_AVAILABLE:
                try:
                    import hashlib
                    
                    # Try to import network
                    try:
                        from pycoin.networks.registry import network_for_netcode
                        if actual_testnet:
                            network = network_for_netcode("XTN")  # Bitcoin testnet
                        else:
                            network = network_for_netcode("BTC")  # Bitcoin mainnet
                    except ImportError:
                        # Fallback to symbols import
                        if actual_testnet and btc_testnet:
                            network = btc_testnet
                        else:
                            network = btc_mainnet
                    
                    if network is None:
                        raise ValueError("Could not load pycoin network")
                    
                    # Parse the key
                    key = network.parse(working_key)
                    
                    if key is None:
                        raise ValueError("Failed to parse key with pycoin")
                    
                    logger.info(f"Parsed key with pycoin")
                    
                    # Derive: 0 (external) -> index (address)
                    external_chain = key.subkey(0)
                    address_key = external_chain.subkey(index)
                    
                    # Get public key and create bech32 address manually
                    pubkey_bytes = address_key.sec()
                    
                    # Hash160
                    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
                    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
                    
                    # Manual bech32 encoding (since segwit_addr import failed)
                    hrp = "tb" if actual_testnet else "bc"
                    addr = _bech32_encode(hrp, 0, ripemd160_hash)
                    
                    logger.info(f"Successfully derived p2wpkh address using pycoin at index {index}: {addr}")
                    return addr
                    
                except Exception as pycoin_error:
                    logger.error(f"pycoin derivation failed: {pycoin_error}")
                    raise ValueError(f"All derivation methods failed. Last error: {pycoin_error}")
            
            raise ValueError("No derivation library succeeded")
            
        elif normalized_key in ["eth", "ethereum"]:
            raise NotImplementedError("Ethereum address derivation not yet implemented")
        else:
            raise NotImplementedError(f"Address derivation for {normalized_key} not yet implemented")
            
    except Exception as e:
        logger.error(f"Address derivation error: {e}")
        raise ValueError(f"Failed to derive address for {network_key}: {e}")


def _bech32_encode(hrp: str, witver: int, witprog: bytes) -> str:
    """
    Manual bech32 encoding for witness addresses.
    Fallback when pycoin.encoding.segwit_addr is not available.
    """
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    
    def bech32_polymod(values):
        GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for v in values:
            b = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ v
            for i in range(5):
                chk ^= GEN[i] if ((b >> i) & 1) else 0
        return chk
    
    def bech32_hrp_expand(hrp):
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    
    def bech32_create_checksum(hrp, data):
        values = bech32_hrp_expand(hrp) + data
        polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
        return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    
    def convertbits(data, frombits, tobits, pad=True):
        acc = 0
        bits = 0
        ret = []
        maxv = (1 << tobits) - 1
        max_acc = (1 << (frombits + tobits - 1)) - 1
        for value in data:
            acc = ((acc << frombits) | value) & max_acc
            bits += frombits
            while bits >= tobits:
                bits -= tobits
                ret.append((acc >> bits) & maxv)
        if pad:
            if bits:
                ret.append((acc << (tobits - bits)) & maxv)
        return ret
    
    # Convert witness program to 5-bit groups
    witprog_5bit = convertbits(witprog, 8, 5)
    
    # Create full data (version + program)
    data = [witver] + witprog_5bit
    
    # Create checksum
    checksum = bech32_create_checksum(hrp, data)
    
    # Combine and encode
    combined = data + checksum
    return hrp + '1' + ''.join([CHARSET[d] for d in combined])


def create_deposit_address(user, network):
    """
    Create a unique deposit address for a user on a network.
    Uses atomic index reservation to prevent address reuse.
    """
    from wallet.models import DepositAddress
    import os
    
    # Reserve next index atomically
    index = reserve_next_index(name=f"{network.key}_{'testnet' if network.is_testnet else 'mainnet'}")
    
    # Derive address from xpub - try multiple sources
    # 1. Network-specific xpub (if set)
    # 2. Environment variable (fresh read each time - most reliable)
    # 3. Django settings (loaded at startup)
    # 4. Direct read from .env file (fallback if env var not available)
    xpub = None
    if network.xpub:
        xpub = network.xpub
        logger.info(f"Using network-specific xpub for {network.key}")
    else:
        # Try environment variable first (most reliable for server processes)
        # Read directly from os.environ to ensure we get the latest value
        xpub = os.environ.get('DEFAULT_XPUB', '')
        if xpub:
            logger.info(f"Using DEFAULT_XPUB from environment for {network.key} (length: {len(xpub)})")
        else:
            # Fallback to settings (may not be updated if env var changed after startup)
            xpub = getattr(settings, 'DEFAULT_XPUB', '')
            if xpub:
                logger.info(f"Using DEFAULT_XPUB from settings for {network.key} (length: {len(xpub)})")
            else:
                # Last resort: read directly from .env file
                try:
                    from pathlib import Path
                    env_path = Path(settings.BASE_DIR) / '.env'
                    if env_path.exists():
                        with open(env_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith('#'):
                                    continue
                                if line.startswith('DEFAULT_XPUB='):
                                    value = line.split('=', 1)[1].strip()
                                    # Remove quotes
                                    if value.startswith('"') and value.endswith('"'):
                                        value = value[1:-1]
                                    elif value.startswith("'") and value.endswith("'"):
                                        value = value[1:-1]
                                    if value:
                                        xpub = value
                                        # Also set it in environment for next time
                                        os.environ['DEFAULT_XPUB'] = value
                                        logger.info(f"Read DEFAULT_XPUB directly from .env file for {network.key} (length: {len(xpub)})")
                                        break
                except Exception as e:
                    logger.debug(f"Failed to read .env file directly: {e}")
    
    # Debug logging to help diagnose issues
    if not xpub:
        logger.error(f"Xpub resolution failed for {network.key}:")
        logger.error(f"  network.xpub: {bool(network.xpub)}")
        logger.error(f"  os.environ.get('DEFAULT_XPUB'): {bool(os.environ.get('DEFAULT_XPUB', ''))}")
        logger.error(f"  settings.DEFAULT_XPUB: {bool(getattr(settings, 'DEFAULT_XPUB', ''))}")
        logger.error(f"  All env vars with 'XPUB': {[k for k in os.environ.keys() if 'XPUB' in k.upper()]}")
        
        error_msg = (
            f"No xpub configured for network {network.key}. "
            f"Set network.xpub in the database or DEFAULT_XPUB environment variable. "
            f"Note: If using environment variable, ensure it's set before starting the Django server."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Using xpub for {network.key}: {xpub[:20]}... (length: {len(xpub)})")
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
    Uses database transactions to prevent race conditions when multiple
    top-ups are created simultaneously.
    
    Args:
        user: User instance
        amount_minor: Amount in USD minor units (cents)
        network: CryptoNetwork instance
        ttl_minutes: Time to live in minutes
    
    Returns:
        TopUpIntent instance
    """
    from wallet.models import TopUpIntent, DepositAddress
    
    # Use atomic transaction to prevent race conditions
    # This ensures that if multiple top-ups are created simultaneously,
    # they don't create duplicate deposit addresses or cause index conflicts
    with transaction.atomic():
        # Get or create deposit address for this user/network
        # Use select_for_update to lock the row during transaction
        deposit_address = DepositAddress.objects.select_for_update().filter(
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