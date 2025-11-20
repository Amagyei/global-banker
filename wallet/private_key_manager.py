"""
Private Key Manager - Handles encryption/decryption of private keys and derivation
"""
import os
import logging
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)

# Try to import HD wallet libraries
try:
    from hdwallet import HDWallet
    from hdwallet.cryptocurrencies import Bitcoin as BitcoinCrypto
    HDWALLET_AVAILABLE = True
except ImportError:
    HDWALLET_AVAILABLE = False
    logger.warning("hdwallet not available - private key derivation may be limited")

try:
    from bip_utils import Bip32Slip10Secp256k1
    BIP_UTILS_AVAILABLE = True
except ImportError:
    BIP_UTILS_AVAILABLE = False
    logger.warning("bip_utils not available - private key derivation may be limited")


class PrivateKeyManager:
    """
    Manages encryption/decryption of extended private keys (xprv) and derivation of private keys.
    Uses AES-256 encryption via Fernet (which uses AES-128 in CBC mode with HMAC).
    For production, consider using AES-256-GCM directly.
    """
    
    def __init__(self):
        # Get encryption key from environment or settings
        # In production, this should be a secure key stored in a key management service
        encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
        if not encryption_key:
            # Generate a key from Django SECRET_KEY (not ideal for production)
            secret_key = getattr(settings, 'SECRET_KEY', '')
            if secret_key:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'wallet_encryption_salt',  # In production, use a random salt per encryption
                    iterations=100000,
                    backend=default_backend()
                )
                encryption_key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
            else:
                raise ValueError("WALLET_ENCRYPTION_KEY must be set in environment or SECRET_KEY must be set")
        
        # Ensure key is bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        # Pad or truncate to 32 bytes for Fernet
        if len(encryption_key) < 32:
            encryption_key = encryption_key.ljust(32, b'0')
        elif len(encryption_key) > 32:
            encryption_key = encryption_key[:32]
        
        # Fernet requires base64-encoded 32-byte key
        self.fernet = Fernet(base64.urlsafe_b64encode(encryption_key))
    
    def encrypt_xprv(self, xprv: str) -> str:
        """
        Encrypt an extended private key (xprv) for storage.
        
        Args:
            xprv: Extended private key string
            
        Returns:
            str: Encrypted xprv (base64 encoded)
        """
        try:
            encrypted = self.fernet.encrypt(xprv.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt xprv: {e}")
            raise ValueError(f"Encryption failed: {e}")
    
    def decrypt_xprv(self, encrypted_xprv: str) -> str:
        """
        Decrypt an encrypted extended private key.
        
        Args:
            encrypted_xprv: Encrypted xprv string
            
        Returns:
            str: Decrypted xprv
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_xprv.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt xprv: {e}")
            raise ValueError(f"Decryption failed: {e}")
    
    def derive_private_key(self, xprv: str, derivation_path: str, network_key: str = 'btc', is_testnet: bool = True) -> str:
        """
        Derive a private key from an extended private key (xprv) at a specific derivation path.
        
        Args:
            xprv: Extended private key
            derivation_path: BIP32 derivation path (e.g., "m/84'/1'/0'/0/0")
            network_key: Network key ("btc", "eth", etc.)
            is_testnet: Whether to use testnet
            
        Returns:
            str: Private key in WIF format (for Bitcoin) or hex format
        """
        if network_key.lower() != 'btc':
            raise NotImplementedError(f"Private key derivation for {network_key} not yet implemented")
        
        if not HDWALLET_AVAILABLE and not BIP_UTILS_AVAILABLE:
            raise ImportError("At least one library (hdwallet or bip_utils) must be installed for private key derivation")
        
        network_str = 'testnet' if is_testnet else 'mainnet'
        
        # Method 1: Try hdwallet
        if HDWALLET_AVAILABLE:
            try:
                hdwallet = HDWallet(cryptocurrency=BitcoinCrypto, network=network_str)
                hdwallet.from_xprivate_key(xprv)
                
                # Derive using path
                # Parse derivation path and derive step by step
                # e.g., "m/84'/1'/0'/0/0" -> derive each component
                path_parts = derivation_path.replace('m/', '').split('/')
                
                for part in path_parts:
                    if part.endswith("'"):
                        # Hardened derivation
                        index = int(part[:-1])
                        hdwallet.from_index(index, hardened=True)
                    else:
                        # Non-hardened derivation
                        index = int(part)
                        hdwallet.from_index(index, hardened=False)
                
                # Get private key in WIF format
                private_key = hdwallet.wif()
                logger.info(f"Derived private key using hdwallet at path {derivation_path}")
                return private_key
                
            except Exception as e:
                logger.warning(f"hdwallet derivation failed: {e}, trying bip_utils")
        
        # Method 2: Try bip_utils
        if BIP_UTILS_AVAILABLE:
            try:
                # Parse derivation path
                path_parts = derivation_path.replace('m/', '').split('/')
                
                # Start with master key
                bip32_ctx = Bip32Slip10Secp256k1.FromExtendedKey(xprv)
                
                # Derive each component
                for part in path_parts:
                    if part.endswith("'"):
                        # Hardened derivation
                        index = int(part[:-1])
                        bip32_ctx = bip32_ctx.ChildKey(index, hardened=True)
                    else:
                        # Non-hardened derivation
                        index = int(part)
                        bip32_ctx = bip32_ctx.ChildKey(index, hardened=False)
                
                # Get private key in WIF format
                private_key = bip32_ctx.PrivateKey().ToWif()
                logger.info(f"Derived private key using bip_utils at path {derivation_path}")
                return private_key
                
            except Exception as e:
                logger.error(f"bip_utils derivation failed: {e}")
                raise ValueError(f"Failed to derive private key: {e}")
        
        raise ValueError("No derivation method succeeded")
    
    def derive_private_key_from_deposit_index(self, xprv: str, deposit_index: int, network_key: str = 'btc', is_testnet: bool = True) -> str:
        """
        Derive a private key for a user deposit address.
        Uses BIP84 derivation: m/84'/1'/0'/0/{index} for testnet or m/84'/0'/0'/0/{index} for mainnet.
        
        Args:
            xprv: Master extended private key
            deposit_index: Deposit address index
            network_key: Network key ("btc")
            is_testnet: Whether to use testnet
            
        Returns:
            str: Private key in WIF format
        """
        # BIP84 derivation path for native SegWit
        # Testnet: m/84'/1'/0'/0/{index}
        # Mainnet: m/84'/0'/0'/0/{index}
        coin_type = 1 if is_testnet else 0
        derivation_path = f"m/84'/{coin_type}'/0'/0/{deposit_index}"
        
        return self.derive_private_key(xprv, derivation_path, network_key, is_testnet)

