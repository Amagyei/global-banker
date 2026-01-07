"""
Fee Estimation Service - Provides accurate transaction fee estimates.
Uses mempool.space API for Bitcoin and other network-specific APIs.
"""
import logging
import requests
from typing import Dict, Optional, Tuple
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache timeout for fee estimates (30 seconds)
FEE_CACHE_TIMEOUT = 30


class FeeEstimator:
    """
    Estimates transaction fees for different cryptocurrency networks.
    Uses real-time fee data from blockchain APIs.
    """
    
    # Fee estimation APIs
    APIS = {
        'btc': {
            'mainnet': 'https://mempool.space/api/v1/fees/recommended',
            'testnet': 'https://mempool.space/testnet/api/v1/fees/recommended',
        },
        'eth': {
            'mainnet': 'https://api.etherscan.io/api?module=gastracker&action=gasoracle',
            'testnet': 'https://api-sepolia.etherscan.io/api?module=gastracker&action=gasoracle',
        },
        'ltc': {
            'mainnet': 'https://api.blockcypher.com/v1/ltc/main',
            'testnet': 'https://api.blockcypher.com/v1/ltc/test3',
        },
    }
    
    # Default fees (satoshis/vbyte for BTC, gwei for ETH)
    DEFAULT_FEES = {
        'btc': {'fast': 50, 'medium': 25, 'slow': 10},
        'eth': {'fast': 50, 'medium': 30, 'slow': 15},
        'ltc': {'fast': 10, 'medium': 5, 'slow': 2},
        'bnb': {'fast': 5, 'medium': 3, 'slow': 1},  # Gwei
        'tron': {'fast': 0, 'medium': 0, 'slow': 0},  # TRON has bandwidth/energy
        'sol': {'fast': 5000, 'medium': 5000, 'slow': 5000},  # Lamports (fixed)
    }
    
    # Typical transaction sizes (vbytes for BTC, gas for ETH)
    TX_SIZES = {
        'btc': {
            'p2wpkh': 140,  # Native SegWit (1 input, 2 outputs)
            'p2sh': 180,    # Wrapped SegWit
            'p2pkh': 226,   # Legacy
        },
        'eth': {
            'transfer': 21000,  # Simple ETH transfer
            'erc20': 65000,     # ERC20 token transfer
        },
        'ltc': {
            'p2wpkh': 140,
            'p2sh': 180,
        },
    }
    
    @classmethod
    def get_fee_estimate(cls, network_key: str, is_testnet: bool = False, priority: str = 'medium') -> Dict:
        """
        Get fee estimate for a network.
        
        Args:
            network_key: Network key (btc, eth, ltc, etc.)
            is_testnet: Whether this is testnet
            priority: Fee priority (fast, medium, slow)
            
        Returns:
            Dict with fee estimates
        """
        network_key = network_key.lower()
        cache_key = f"fee_estimate:{network_key}:{'testnet' if is_testnet else 'mainnet'}"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch from API
        try:
            if network_key == 'btc':
                fees = cls._get_bitcoin_fees(is_testnet)
            elif network_key == 'eth':
                fees = cls._get_ethereum_fees(is_testnet)
            elif network_key == 'ltc':
                fees = cls._get_litecoin_fees(is_testnet)
            else:
                fees = cls._get_default_fees(network_key)
            
            # Cache the result
            cache.set(cache_key, fees, FEE_CACHE_TIMEOUT)
            return fees
            
        except Exception as e:
            logger.error(f"Failed to get fee estimate for {network_key}: {e}")
            return cls._get_default_fees(network_key)
    
    @classmethod
    def _get_bitcoin_fees(cls, is_testnet: bool = False) -> Dict:
        """Get Bitcoin fee estimates from mempool.space"""
        try:
            url = cls.APIS['btc']['testnet' if is_testnet else 'mainnet']
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # mempool.space returns: fastestFee, halfHourFee, hourFee, economyFee, minimumFee
            return {
                'fast': data.get('fastestFee', 50),        # Next block
                'medium': data.get('halfHourFee', 25),     # ~30 minutes
                'slow': data.get('hourFee', 10),           # ~1 hour
                'economy': data.get('economyFee', 5),      # No time guarantee
                'minimum': data.get('minimumFee', 1),      # Minimum relay fee
                'unit': 'sat/vB',
                'source': 'mempool.space',
                'network': 'testnet' if is_testnet else 'mainnet',
            }
        except Exception as e:
            logger.error(f"Bitcoin fee API error: {e}")
            return cls._get_default_fees('btc')
    
    @classmethod
    def _get_ethereum_fees(cls, is_testnet: bool = False) -> Dict:
        """Get Ethereum gas price estimates"""
        try:
            url = cls.APIS['eth']['testnet' if is_testnet else 'mainnet']
            api_key = getattr(settings, 'ETHERSCAN_API_KEY', '')
            if api_key:
                url += f"&apikey={api_key}"
            
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1':
                result = data.get('result', {})
                return {
                    'fast': int(result.get('FastGasPrice', 50)),
                    'medium': int(result.get('ProposeGasPrice', 30)),
                    'slow': int(result.get('SafeGasPrice', 15)),
                    'base_fee': int(result.get('suggestBaseFee', 0)),
                    'unit': 'gwei',
                    'source': 'etherscan',
                    'network': 'testnet' if is_testnet else 'mainnet',
                }
        except Exception as e:
            logger.error(f"Ethereum fee API error: {e}")
        
        return cls._get_default_fees('eth')
    
    @classmethod
    def _get_litecoin_fees(cls, is_testnet: bool = False) -> Dict:
        """Get Litecoin fee estimates from BlockCypher"""
        try:
            url = cls.APIS['ltc']['testnet' if is_testnet else 'mainnet']
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # BlockCypher returns fees in satoshis/kB, convert to sat/vB
            high_fee = data.get('high_fee_per_kb', 10000) // 1000
            medium_fee = data.get('medium_fee_per_kb', 5000) // 1000
            low_fee = data.get('low_fee_per_kb', 2000) // 1000
            
            return {
                'fast': high_fee,
                'medium': medium_fee,
                'slow': low_fee,
                'unit': 'sat/vB',
                'source': 'blockcypher',
                'network': 'testnet' if is_testnet else 'mainnet',
            }
        except Exception as e:
            logger.error(f"Litecoin fee API error: {e}")
        
        return cls._get_default_fees('ltc')
    
    @classmethod
    def _get_default_fees(cls, network_key: str) -> Dict:
        """Get default fee estimates"""
        defaults = cls.DEFAULT_FEES.get(network_key, {'fast': 10, 'medium': 5, 'slow': 2})
        return {
            **defaults,
            'unit': 'sat/vB' if network_key in ['btc', 'ltc'] else 'gwei',
            'source': 'default',
            'network': 'unknown',
        }
    
    @classmethod
    def estimate_transaction_fee(
        cls,
        network_key: str,
        is_testnet: bool = False,
        priority: str = 'medium',
        tx_type: str = 'p2wpkh',
        num_inputs: int = 1,
        num_outputs: int = 2
    ) -> Tuple[int, str]:
        """
        Estimate total transaction fee in atomic units.
        
        Args:
            network_key: Network key (btc, eth, ltc, etc.)
            is_testnet: Whether this is testnet
            priority: Fee priority (fast, medium, slow)
            tx_type: Transaction type (p2wpkh, p2sh, p2pkh, transfer, erc20)
            num_inputs: Number of inputs (for UTXO chains)
            num_outputs: Number of outputs (for UTXO chains)
            
        Returns:
            Tuple of (fee_in_atomic_units, fee_description)
        """
        network_key = network_key.lower()
        fees = cls.get_fee_estimate(network_key, is_testnet)
        fee_rate = fees.get(priority, fees.get('medium', 10))
        
        if network_key in ['btc', 'ltc']:
            # UTXO-based: fee = fee_rate * tx_size
            base_size = cls.TX_SIZES.get(network_key, {}).get(tx_type, 140)
            # Estimate size based on inputs/outputs
            # Each additional input adds ~68 vbytes (P2WPKH)
            # Each additional output adds ~31 vbytes
            tx_size = base_size + (num_inputs - 1) * 68 + (num_outputs - 2) * 31
            fee = fee_rate * tx_size
            return fee, f"{fee} satoshis ({fee_rate} sat/vB × {tx_size} vB)"
        
        elif network_key in ['eth', 'bnb']:
            # Account-based: fee = gas_price * gas_limit
            gas_limit = cls.TX_SIZES.get('eth', {}).get(tx_type, 21000)
            # Convert gwei to wei
            fee_wei = fee_rate * 10**9 * gas_limit
            return fee_wei, f"{fee_wei} wei ({fee_rate} gwei × {gas_limit} gas)"
        
        elif network_key == 'sol':
            # Solana has fixed fees
            fee = 5000  # 5000 lamports
            return fee, f"{fee} lamports (fixed)"
        
        elif network_key in ['tron', 'usdt']:
            # TRON uses bandwidth/energy, typically free for simple transfers
            return 0, "0 TRX (uses bandwidth)"
        
        else:
            # Default
            return fee_rate * 200, f"{fee_rate * 200} atomic units"
    
    @classmethod
    def estimate_sweep_fee(
        cls,
        network_key: str,
        is_testnet: bool = False,
        priority: str = 'medium'
    ) -> int:
        """
        Estimate fee for sweeping funds from deposit address to hot wallet.
        Uses conservative estimates for reliable sweeps.
        
        Returns:
            Fee in atomic units (satoshis, wei, etc.)
        """
        # Use medium priority for sweeps
        fee, _ = cls.estimate_transaction_fee(
            network_key=network_key,
            is_testnet=is_testnet,
            priority=priority,
            tx_type='p2wpkh',
            num_inputs=1,
            num_outputs=1  # Single output to hot wallet
        )
        
        # Add 10% buffer for fee estimation uncertainty
        return int(fee * 1.1)
    
    @classmethod
    def is_dust(cls, amount_atomic: int, network_key: str) -> bool:
        """
        Check if amount is dust (too small to be economically spent).
        
        Args:
            amount_atomic: Amount in atomic units
            network_key: Network key
            
        Returns:
            True if amount is dust
        """
        # Dust thresholds (in atomic units)
        dust_thresholds = {
            'btc': 546,      # 546 satoshis (P2WPKH dust limit)
            'ltc': 546,      # Same as BTC
            'eth': 10**15,   # 0.001 ETH
            'bnb': 10**15,   # 0.001 BNB
            'sol': 890880,   # Rent-exempt minimum
            'tron': 0,       # No dust limit
        }
        
        threshold = dust_thresholds.get(network_key.lower(), 1000)
        return amount_atomic < threshold


def get_recommended_fee(network_key: str, is_testnet: bool = False, priority: str = 'medium') -> Dict:
    """
    Convenience function to get recommended fee.
    
    Returns:
        Dict with fee estimate
    """
    return FeeEstimator.get_fee_estimate(network_key, is_testnet, priority)


def estimate_tx_fee(
    network_key: str,
    is_testnet: bool = False,
    priority: str = 'medium',
    tx_type: str = 'p2wpkh'
) -> Tuple[int, str]:
    """
    Convenience function to estimate transaction fee.
    
    Returns:
        Tuple of (fee_amount, description)
    """
    return FeeEstimator.estimate_transaction_fee(network_key, is_testnet, priority, tx_type)

