"""
Cryptocurrency address validation module.
Validates addresses for BTC, ETH, and other supported networks.
"""
import re
import logging
import hashlib
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Try to import validation libraries
try:
    from eth_utils import is_address as is_eth_address, is_checksum_address
    ETH_UTILS_AVAILABLE = True
except ImportError:
    ETH_UTILS_AVAILABLE = False
    logger.warning("eth_utils not available - Ethereum address validation will be basic")

try:
    import base58
    BASE58_AVAILABLE = True
except ImportError:
    BASE58_AVAILABLE = False
    logger.warning("base58 not available - Bitcoin address validation will be basic")


class AddressValidator:
    """
    Validates cryptocurrency addresses for supported networks.
    """
    
    # Address patterns for basic validation
    PATTERNS = {
        'btc_legacy': r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$',  # P2PKH or P2SH
        'btc_segwit': r'^bc1[a-z0-9]{39,59}$',  # Bech32 mainnet
        'btc_segwit_testnet': r'^tb1[a-z0-9]{39,59}$',  # Bech32 testnet
        'eth': r'^0x[a-fA-F0-9]{40}$',  # Ethereum
        'tron': r'^T[a-zA-Z0-9]{33}$',  # TRON
        'solana': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',  # Solana (Base58)
        'ltc_legacy': r'^[LM3][a-km-zA-HJ-NP-Z1-9]{25,34}$',  # Litecoin P2PKH/P2SH
        'ltc_segwit': r'^ltc1[a-z0-9]{39,59}$',  # Litecoin Bech32
        'bnb': r'^0x[a-fA-F0-9]{40}$',  # BNB (same as ETH)
    }
    
    @classmethod
    def validate_address(cls, address: str, network_key: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate a cryptocurrency address.
        
        Args:
            address: The address to validate
            network_key: Network key (btc, eth, tron, sol, ltc, bnb)
            is_testnet: Whether this is a testnet address
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not address:
            return False, "Address is required"
        
        address = address.strip()
        network_key = network_key.lower()
        
        # Route to appropriate validator
        validators = {
            'btc': cls._validate_bitcoin,
            'eth': cls._validate_ethereum,
            'tron': cls._validate_tron,
            'usdt': cls._validate_tron,  # USDT on TRON
            'usdc': cls._validate_ethereum,  # USDC on Ethereum
            'sol': cls._validate_solana,
            'ltc': cls._validate_litecoin,
            'bnb': cls._validate_ethereum,  # BNB uses Ethereum format
        }
        
        validator = validators.get(network_key)
        if not validator:
            return False, f"Unsupported network: {network_key}"
        
        return validator(address, is_testnet)
    
    @classmethod
    def _validate_bitcoin(cls, address: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate Bitcoin address"""
        # Check for Bech32 (native SegWit)
        if address.startswith('bc1') or address.startswith('tb1'):
            if is_testnet and not address.startswith('tb1'):
                return False, "Testnet Bitcoin address should start with 'tb1'"
            if not is_testnet and not address.startswith('bc1'):
                return False, "Mainnet Bitcoin address should start with 'bc1'"
            
            pattern = cls.PATTERNS['btc_segwit_testnet'] if is_testnet else cls.PATTERNS['btc_segwit']
            if not re.match(pattern, address):
                return False, "Invalid Bech32 Bitcoin address format"
            
            # Bech32 checksum validation
            if not cls._validate_bech32_checksum(address):
                return False, "Invalid Bech32 checksum"
            
            return True, None
        
        # Check for legacy (P2PKH or P2SH)
        if re.match(cls.PATTERNS['btc_legacy'], address):
            # Testnet legacy addresses start with 'm', 'n', or '2'
            if is_testnet and address[0] not in ['m', 'n', '2']:
                return False, "Testnet Bitcoin address should start with 'm', 'n', or '2'"
            if not is_testnet and address[0] not in ['1', '3']:
                return False, "Mainnet Bitcoin address should start with '1' or '3'"
            
            # Base58Check validation
            if BASE58_AVAILABLE:
                try:
                    decoded = base58.b58decode_check(address)
                    return True, None
                except Exception:
                    return False, "Invalid Base58Check encoding"
            
            return True, None
        
        return False, "Invalid Bitcoin address format"
    
    @classmethod
    def _validate_ethereum(cls, address: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate Ethereum address (also works for BNB, USDC)"""
        if not re.match(cls.PATTERNS['eth'], address):
            return False, "Invalid Ethereum address format (should start with 0x followed by 40 hex characters)"
        
        # Use eth_utils for proper validation if available
        if ETH_UTILS_AVAILABLE:
            if not is_eth_address(address):
                return False, "Invalid Ethereum address"
            
            # Check checksum if address has mixed case
            if address != address.lower() and address != address.upper():
                if not is_checksum_address(address):
                    return False, "Invalid Ethereum address checksum"
        
        return True, None
    
    @classmethod
    def _validate_tron(cls, address: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate TRON address (also used for USDT on TRON)"""
        if not re.match(cls.PATTERNS['tron'], address):
            return False, "Invalid TRON address format (should start with 'T' followed by 33 alphanumeric characters)"
        
        # Base58Check validation
        if BASE58_AVAILABLE:
            try:
                decoded = base58.b58decode_check(address)
                # TRON addresses should decode to 21 bytes
                if len(decoded) != 21:
                    return False, "Invalid TRON address length"
                # First byte should be 0x41 for mainnet
                if decoded[0] != 0x41:
                    return False, "Invalid TRON address prefix"
                return True, None
            except Exception:
                return False, "Invalid TRON address encoding"
        
        return True, None
    
    @classmethod
    def _validate_solana(cls, address: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate Solana address"""
        if not re.match(cls.PATTERNS['solana'], address):
            return False, "Invalid Solana address format"
        
        # Base58 validation
        if BASE58_AVAILABLE:
            try:
                decoded = base58.b58decode(address)
                # Solana addresses should be 32 bytes
                if len(decoded) != 32:
                    return False, "Invalid Solana address length"
                return True, None
            except Exception:
                return False, "Invalid Solana address encoding"
        
        return True, None
    
    @classmethod
    def _validate_litecoin(cls, address: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate Litecoin address"""
        # Check for Bech32 (native SegWit)
        if address.startswith('ltc1'):
            if not re.match(cls.PATTERNS['ltc_segwit'], address):
                return False, "Invalid Litecoin Bech32 address format"
            return True, None
        
        # Check for legacy
        if re.match(cls.PATTERNS['ltc_legacy'], address):
            if BASE58_AVAILABLE:
                try:
                    base58.b58decode_check(address)
                    return True, None
                except Exception:
                    return False, "Invalid Litecoin address encoding"
            return True, None
        
        return False, "Invalid Litecoin address format"
    
    @classmethod
    def _validate_bech32_checksum(cls, address: str) -> bool:
        """Validate Bech32 checksum"""
        CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        
        try:
            # Find the separator
            pos = address.rfind('1')
            if pos < 1 or pos + 7 > len(address):
                return False
            
            hrp = address[:pos].lower()
            data_part = address[pos + 1:].lower()
            
            # Check characters
            if not all(c in CHARSET for c in data_part):
                return False
            
            # Convert to 5-bit values
            values = [CHARSET.find(c) for c in data_part]
            
            # Polymod verification
            def bech32_polymod(values):
                GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
                chk = 1
                for v in values:
                    b = chk >> 25
                    chk = ((chk & 0x1ffffff) << 5) ^ v
                    for i in range(5):
                        chk ^= GEN[i] if ((b >> i) & 1) else 0
                return chk
            
            def bech32_hrp_expand(hrp):
                return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
            
            return bech32_polymod(bech32_hrp_expand(hrp) + values) == 1
            
        except Exception:
            return False
    
    @classmethod
    def get_address_type(cls, address: str, network_key: str) -> Optional[str]:
        """
        Get the type of address (legacy, segwit, etc.)
        
        Returns:
            Address type string or None if invalid
        """
        network_key = network_key.lower()
        
        if network_key == 'btc':
            if address.startswith('bc1') or address.startswith('tb1'):
                return 'native_segwit'
            elif address.startswith('3') or address.startswith('2'):
                return 'segwit_p2sh'
            elif address.startswith('1') or address.startswith('m') or address.startswith('n'):
                return 'legacy'
        elif network_key in ['eth', 'bnb', 'usdc']:
            return 'ethereum'
        elif network_key in ['tron', 'usdt']:
            return 'tron'
        elif network_key == 'sol':
            return 'solana'
        elif network_key == 'ltc':
            if address.startswith('ltc1'):
                return 'native_segwit'
            else:
                return 'legacy'
        
        return None


def validate_deposit_address(address: str, network_key: str, is_testnet: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to validate a deposit address.
    
    Args:
        address: The address to validate
        network_key: Network key (btc, eth, tron, sol, ltc, bnb)
        is_testnet: Whether this is a testnet address
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    return AddressValidator.validate_address(address, network_key, is_testnet)

