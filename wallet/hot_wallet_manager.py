"""
Hot Wallet Manager - Manages hot wallet and consolidates funds to cold wallet
"""
import logging
import requests
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

logger = logging.getLogger(__name__)

# Try to import Bitcoin transaction libraries
try:
    from bit import PrivateKeyTestnet, PrivateKey
    BIT_AVAILABLE = True
except ImportError:
    BIT_AVAILABLE = False
    logger.warning("bit library not available - consolidation functionality will be limited")

from .models import HotWallet, ColdWallet, ConsolidationTransaction, CryptoNetwork
from .private_key_manager import PrivateKeyManager


class HotWalletManager:
    """
    Manages hot wallet operations and consolidates funds to cold wallet.
    """
    
    def __init__(self):
        self.key_manager = PrivateKeyManager()
    
    def consolidate_to_cold(
        self,
        network: CryptoNetwork,
        threshold_atomic: int = None,
        force: bool = False
    ) -> ConsolidationTransaction:
        """
        Consolidate hot wallet funds to cold wallet.
        
        Args:
            network: CryptoNetwork to consolidate
            threshold_atomic: Minimum balance to trigger consolidation (default: 0.01 BTC equivalent)
            force: If True, consolidate regardless of threshold
            
        Returns:
            ConsolidationTransaction: Created consolidation transaction
        """
        # Get hot wallet
        hot_wallet = HotWallet.objects.filter(
            network=network,
            is_active=True
        ).first()
        
        if not hot_wallet:
            raise ValueError(f"No active hot wallet found for network {network.key}")
        
        # Get cold wallet
        cold_wallet = ColdWallet.objects.filter(
            network=network,
            is_active=True
        ).first()
        
        if not cold_wallet:
            raise ValueError(f"No active cold wallet found for network {network.key}")
        
        # Get hot wallet balance
        balance = self._get_address_balance(hot_wallet.address, network)
        
        # Set default threshold if not provided (0.01 BTC equivalent)
        if threshold_atomic is None:
            if network.native_symbol.upper() == 'BTC':
                threshold_atomic = 1000000  # 0.01 BTC in satoshis
            else:
                threshold_atomic = 10000000000000000  # 0.01 ETH in wei (rough estimate)
        
        # Check if balance exceeds threshold
        if not force and balance < threshold_atomic:
            logger.info(
                f"Hot wallet balance {balance} below threshold {threshold_atomic} for {network.key}. "
                f"Skipping consolidation."
            )
            raise ValueError(f"Balance {balance} below threshold {threshold_atomic}")
        
        # Decrypt hot wallet private key
        try:
            xprv = self.key_manager.decrypt_xprv(hot_wallet.encrypted_xprv)
        except Exception as e:
            logger.error(f"Failed to decrypt hot wallet xprv: {e}")
            raise ValueError(f"Hot wallet decryption failed: {e}")
        
        # Derive private key for hot wallet
        try:
            private_key_wif = self.key_manager.derive_private_key(
                xprv,
                hot_wallet.derivation_path,
                network.key,
                network.effective_is_testnet
            )
        except Exception as e:
            logger.error(f"Failed to derive hot wallet private key: {e}")
            raise ValueError(f"Private key derivation failed: {e}")
        
        # Create and broadcast consolidation transaction
        try:
            consolidation_tx = self._create_and_broadcast_consolidation(
                hot_wallet=hot_wallet,
                cold_wallet=cold_wallet,
                network=network,
                balance=balance,
                private_key_wif=private_key_wif
            )
            return consolidation_tx
        except Exception as e:
            logger.error(f"Failed to create/broadcast consolidation: {e}")
            # Create failed consolidation transaction record
            return self._create_failed_consolidation(
                hot_wallet=hot_wallet,
                cold_wallet=cold_wallet,
                network=network,
                balance=balance,
                error_message=str(e)
            )
    
    def _get_address_balance(self, address: str, network: CryptoNetwork) -> int:
        """Get balance of an address in atomic units"""
        try:
            # Use Blockstream API
            base_url = network.effective_explorer_api_url.rstrip('/')
            if network.effective_is_testnet:
                if 'blockstream' in base_url.lower():
                    api_url = f"{base_url}/address/{address}"
                else:
                    api_url = f"{base_url}/address/{address}/balance"
            else:
                api_url = f"{base_url}/address/{address}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Blockstream returns balance directly or in chain_stats
            if isinstance(data, dict):
                if 'chain_stats' in data:
                    balance = data['chain_stats'].get('funded_txo_sum', 0) - data['chain_stats'].get('spent_txo_sum', 0)
                else:
                    balance = data.get('balance', data.get('funded_txo_sum', 0) - data.get('spent_txo_sum', 0))
            else:
                balance = int(data)
            
            return max(0, balance)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise ValueError(f"Balance check failed: {e}")
    
    def _create_and_broadcast_consolidation(
        self,
        hot_wallet: HotWallet,
        cold_wallet: ColdWallet,
        network: CryptoNetwork,
        balance: int,
        private_key_wif: str
    ) -> ConsolidationTransaction:
        """Create and broadcast consolidation transaction"""
        if not BIT_AVAILABLE:
            raise ImportError("bit library required for consolidation transactions")
        
        is_testnet = network.effective_is_testnet
        
        # Create private key object
        if is_testnet:
            key = PrivateKeyTestnet(private_key_wif)
        else:
            key = PrivateKey(private_key_wif)
        
        # Estimate fee
        fee_estimate = self._estimate_fee(network, is_testnet)
        
        # Calculate consolidation amount (balance - fee)
        consolidation_amount = balance - fee_estimate
        if consolidation_amount <= 0:
            raise ValueError(f"Insufficient balance to cover fees. Balance: {balance}, Fee: {fee_estimate}")
        
        # Create consolidation transaction
        try:
            # Use bit library to create transaction
            tx_hex = key.create_transaction(
                [(cold_wallet.address, consolidation_amount, 'satoshi')],
                fee=fee_estimate,
                leftover=cold_wallet.address  # Send change back to cold wallet
            )
            
            # Broadcast transaction
            tx_hash = self._broadcast_transaction(tx_hex, network)
            
            logger.info(f"Broadcast consolidation transaction {tx_hash} from {hot_wallet.address} to {cold_wallet.address}")
            
        except Exception as e:
            # Fallback: try using key.send() directly
            logger.warning(f"create_transaction failed: {e}, trying key.send()")
            try:
                tx_hash = key.send([(cold_wallet.address, consolidation_amount, 'satoshi')], fee=fee_estimate)
                logger.info(f"Broadcast consolidation transaction {tx_hash} using key.send()")
            except Exception as send_error:
                raise ValueError(f"Failed to create/broadcast consolidation transaction: {send_error}")
        
        # Create ConsolidationTransaction record
        with transaction.atomic():
            consolidation_tx = ConsolidationTransaction.objects.create(
                network=network,
                from_address=hot_wallet.address,
                to_address=cold_wallet.address,
                amount_atomic=consolidation_amount,
                tx_hash=tx_hash,
                fee_atomic=fee_estimate,
                status='broadcast',
                hot_wallet=hot_wallet,
                cold_wallet=cold_wallet,
                required_confirmations=2
            )
            
            # Update hot wallet
            hot_wallet.last_consolidation_at = timezone.now()
            hot_wallet.balance_atomic = 0  # Assume all funds consolidated
            hot_wallet.save(update_fields=['last_consolidation_at', 'balance_atomic'])
        
        return consolidation_tx
    
    def _estimate_fee(self, network: CryptoNetwork, is_testnet: bool) -> int:
        """Estimate transaction fee"""
        if is_testnet:
            return 1000  # 1000 satoshis for testnet
        else:
            return 10000  # 10000 satoshis for mainnet (conservative)
    
    def _broadcast_transaction(self, tx_hex: str, network: CryptoNetwork) -> str:
        """Broadcast transaction to blockchain"""
        base_url = network.effective_explorer_api_url.rstrip('/')
        
        # Blockstream API endpoint
        if 'blockstream' in base_url.lower():
            if network.effective_is_testnet:
                broadcast_url = 'https://blockstream.info/testnet/api/tx'
            else:
                broadcast_url = 'https://blockstream.info/api/tx'
        else:
            broadcast_url = f"{base_url}/tx"
        
        try:
            response = requests.post(
                broadcast_url,
                data=tx_hex,
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )
            response.raise_for_status()
            
            # Blockstream returns the tx hash
            tx_hash = response.text.strip()
            return tx_hash
            
        except Exception as e:
            logger.error(f"Failed to broadcast transaction: {e}")
            raise ValueError(f"Transaction broadcast failed: {e}")
    
    def _create_failed_consolidation(
        self,
        hot_wallet: HotWallet,
        cold_wallet: ColdWallet,
        network: CryptoNetwork,
        balance: int,
        error_message: str
    ) -> ConsolidationTransaction:
        """Create a failed consolidation transaction record"""
        return ConsolidationTransaction.objects.create(
            network=network,
            from_address=hot_wallet.address,
            to_address=cold_wallet.address,
            amount_atomic=balance,
            status='failed',
            hot_wallet=hot_wallet,
            cold_wallet=cold_wallet,
            error_message=error_message,
            retry_count=0
        )
    
    def retry_failed_consolidation(self, consolidation_tx: ConsolidationTransaction) -> ConsolidationTransaction:
        """Retry a failed consolidation transaction"""
        if consolidation_tx.status != 'failed':
            raise ValueError(f"Cannot retry consolidation with status {consolidation_tx.status}")
        
        if consolidation_tx.retry_count >= consolidation_tx.max_retries:
            raise ValueError(f"Max retries ({consolidation_tx.max_retries}) exceeded for consolidation {consolidation_tx.id}")
        
        # Reset status and increment retry count
        consolidation_tx.status = 'pending'
        consolidation_tx.retry_count += 1
        consolidation_tx.error_message = ''
        consolidation_tx.save()
        
        # Retry the consolidation
        try:
            return self.consolidate_to_cold(
                consolidation_tx.network,
                threshold_atomic=consolidation_tx.amount_atomic,
                force=True
            )
        except Exception as e:
            # Mark as failed again
            consolidation_tx.status = 'failed'
            consolidation_tx.error_message = str(e)
            consolidation_tx.save()
            raise

