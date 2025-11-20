"""
Sweep Service - Sweeps funds from user deposit addresses to hot wallet
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
    logger.warning("bit library not available - sweep functionality will be limited")

from .models import (
    HotWallet, SweepTransaction, OnChainTransaction, DepositAddress, CryptoNetwork
)
from .private_key_manager import PrivateKeyManager
from .exchange_rates import convert_crypto_to_usd


class SweepService:
    """
    Service to sweep funds from user deposit addresses to hot wallet.
    Derives private keys from master xprv, creates and broadcasts sweep transactions.
    """
    
    def __init__(self):
        self.key_manager = PrivateKeyManager()
    
    def sweep_deposit(self, onchain_tx: OnChainTransaction) -> SweepTransaction:
        """
        Sweep funds from a user deposit address to the hot wallet.
        
        Args:
            onchain_tx: Confirmed OnChainTransaction to sweep
            
        Returns:
            SweepTransaction: Created sweep transaction record
            
        Raises:
            ValueError: If sweep cannot be performed
        """
        # Check if already swept
        if hasattr(onchain_tx, 'sweep_transaction'):
            existing_sweep = onchain_tx.sweep_transaction
            logger.info(f"Transaction {onchain_tx.tx_hash} already has sweep: {existing_sweep.id}")
            return existing_sweep
        
        # Get deposit address
        deposit_address = DepositAddress.objects.filter(
            address=onchain_tx.to_address,
            network=onchain_tx.network,
            user=onchain_tx.user
        ).first()
        
        if not deposit_address:
            raise ValueError(f"Deposit address {onchain_tx.to_address} not found for user {onchain_tx.user.email}")
        
        # Get or create hot wallet for this network
        hot_wallet = HotWallet.objects.filter(
            network=onchain_tx.network,
            is_active=True
        ).first()
        
        if not hot_wallet:
            raise ValueError(f"No active hot wallet found for network {onchain_tx.network.key}")
        
        # Get master xprv from environment or settings
        master_xprv = self._get_master_xprv()
        if not master_xprv:
            raise ValueError("Master xprv not configured. Set MASTER_XPRV environment variable.")
        
        # Derive private key for deposit address
        try:
            private_key_wif = self.key_manager.derive_private_key_from_deposit_index(
                master_xprv,
                deposit_address.index,
                onchain_tx.network.key,
                onchain_tx.network.effective_is_testnet
            )
        except Exception as e:
            logger.error(f"Failed to derive private key for deposit address {deposit_address.address}: {e}")
            raise ValueError(f"Private key derivation failed: {e}")
        
        # Create sweep transaction
        try:
            sweep_tx = self._create_and_broadcast_sweep(
                onchain_tx=onchain_tx,
                deposit_address=deposit_address,
                hot_wallet=hot_wallet,
                private_key_wif=private_key_wif
            )
            return sweep_tx
        except Exception as e:
            logger.error(f"Failed to create/broadcast sweep: {e}")
            # Create failed sweep transaction record
            return self._create_failed_sweep(
                onchain_tx=onchain_tx,
                deposit_address=deposit_address,
                hot_wallet=hot_wallet,
                error_message=str(e)
            )
    
    def _get_master_xprv(self) -> str:
        """Get master xprv from environment or settings"""
        import os
        from django.conf import settings
        
        # Try environment variable first
        master_xprv = os.getenv('MASTER_XPRV', '')
        if master_xprv:
            return master_xprv
        
        # Try settings
        master_xprv = getattr(settings, 'MASTER_XPRV', '')
        if master_xprv:
            return master_xprv
        
        return None
    
    def _create_and_broadcast_sweep(
        self,
        onchain_tx: OnChainTransaction,
        deposit_address: DepositAddress,
        hot_wallet: HotWallet,
        private_key_wif: str
    ) -> SweepTransaction:
        """
        Create and broadcast a sweep transaction.
        
        Returns:
            SweepTransaction: Created sweep transaction
        """
        network = onchain_tx.network
        is_testnet = network.effective_is_testnet
        
        if not BIT_AVAILABLE:
            raise ImportError("bit library required for sweep transactions")
        
        # Create private key object
        if is_testnet:
            key = PrivateKeyTestnet(private_key_wif)
        else:
            key = PrivateKey(private_key_wif)
        
        # Get balance of deposit address
        balance = self._get_address_balance(deposit_address.address, network)
        if balance <= 0:
            raise ValueError(f"Deposit address {deposit_address.address} has no balance to sweep")
        
        # Estimate fee (use a conservative estimate)
        fee_estimate = self._estimate_fee(network, is_testnet)
        
        # Calculate sweep amount (balance - fee)
        sweep_amount = balance - fee_estimate
        if sweep_amount <= 0:
            raise ValueError(f"Insufficient balance to cover fees. Balance: {balance}, Fee: {fee_estimate}")
        
        # Create sweep transaction
        try:
            # Use bit library to create transaction
            # For now, we'll use a simple send - in production, you might want more control
            tx_hex = key.create_transaction(
                [(hot_wallet.address, sweep_amount, 'satoshi')],
                fee=fee_estimate,
                leftover=hot_wallet.address  # Send change back to hot wallet
            )
            
            # Broadcast transaction
            tx_hash = self._broadcast_transaction(tx_hex, network)
            
            logger.info(f"Broadcast sweep transaction {tx_hash} from {deposit_address.address} to {hot_wallet.address}")
            
        except Exception as e:
            # Fallback: try using key.send() directly
            logger.warning(f"create_transaction failed: {e}, trying key.send()")
            try:
                tx_hash = key.send([(hot_wallet.address, sweep_amount, 'satoshi')], fee=fee_estimate)
                logger.info(f"Broadcast sweep transaction {tx_hash} using key.send()")
            except Exception as send_error:
                raise ValueError(f"Failed to create/broadcast sweep transaction: {send_error}")
        
        # Create SweepTransaction record
        with transaction.atomic():
            sweep_tx = SweepTransaction.objects.create(
                user=onchain_tx.user,
                network=network,
                from_address=deposit_address.address,
                to_address=hot_wallet.address,
                amount_atomic=sweep_amount,
                tx_hash=tx_hash,
                fee_atomic=fee_estimate,
                status='broadcast',
                onchain_tx=onchain_tx,
                hot_wallet=hot_wallet,
                required_confirmations=1  # Sweeps need fewer confirmations
            )
            
            # Update hot wallet last_sweep_at
            hot_wallet.last_sweep_at = timezone.now()
            hot_wallet.save(update_fields=['last_sweep_at'])
        
        return sweep_tx
    
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
    
    def _estimate_fee(self, network: CryptoNetwork, is_testnet: bool) -> int:
        """
        Estimate transaction fee.
        For now, use a fixed fee. In production, use fee estimation API.
        """
        # Conservative fee estimate
        # Testnet: lower fees, Mainnet: higher fees
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
    
    def _create_failed_sweep(
        self,
        onchain_tx: OnChainTransaction,
        deposit_address: DepositAddress,
        hot_wallet: HotWallet,
        error_message: str
    ) -> SweepTransaction:
        """Create a failed sweep transaction record"""
        return SweepTransaction.objects.create(
            user=onchain_tx.user,
            network=onchain_tx.network,
            from_address=deposit_address.address,
            to_address=hot_wallet.address,
            amount_atomic=onchain_tx.amount_atomic,
            status='failed',
            onchain_tx=onchain_tx,
            hot_wallet=hot_wallet,
            error_message=error_message,
            retry_count=0
        )
    
    def retry_failed_sweep(self, sweep_tx: SweepTransaction) -> SweepTransaction:
        """
        Retry a failed sweep transaction.
        
        Args:
            sweep_tx: Failed SweepTransaction to retry
            
        Returns:
            SweepTransaction: Updated sweep transaction
        """
        if sweep_tx.status != 'failed':
            raise ValueError(f"Cannot retry sweep with status {sweep_tx.status}")
        
        if sweep_tx.retry_count >= sweep_tx.max_retries:
            raise ValueError(f"Max retries ({sweep_tx.max_retries}) exceeded for sweep {sweep_tx.id}")
        
        # Reset status and increment retry count
        sweep_tx.status = 'pending'
        sweep_tx.retry_count += 1
        sweep_tx.error_message = ''
        sweep_tx.save()
        
        # Retry the sweep
        try:
            return self.sweep_deposit(sweep_tx.onchain_tx)
        except Exception as e:
            # Mark as failed again
            sweep_tx.status = 'failed'
            sweep_tx.error_message = str(e)
            sweep_tx.save()
            raise

