"""
Blockchain monitoring and transaction verification using Blockstream Esplora API
"""
import requests
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class BlockchainMonitor:
    """Monitor blockchain for transactions using Blockstream Esplora API"""
    
    def __init__(self, network):
        self.network = network
        # Use effective explorer API URL (respects WALLET_TEST_MODE)
        self.base_url = network.effective_explorer_api_url.rstrip('/')
        self.timeout = 10
    
    def get_current_block_height(self):
        """Get current block height"""
        try:
            if 'blockstream' in self.base_url.lower():
                # Blockstream Esplora API
                response = requests.get(f"{self.base_url}/blocks/tip/height", timeout=self.timeout)
                return int(response.text)
            else:
                # Generic API - may need different endpoint
                response = requests.get(f"{self.base_url}/blocks/tip/height", timeout=self.timeout)
                return int(response.text)
        except Exception as e:
            logger.error(f"Error getting block height: {e}")
            return None
    
    def get_address_transactions(self, address):
        """Get all transactions for an address"""
        try:
            # Detect testnet address by prefix (tb1 for testnet bech32)
            is_testnet_address = address.startswith('tb1') or address.startswith('2') or address.startswith('m') or address.startswith('n')
            # Use effective testnet status (respects WALLET_TEST_MODE), but also check address format
            use_testnet = self.network.effective_is_testnet or is_testnet_address
            
            # Blockstream Esplora API - use testnet endpoint if needed
            if 'blockstream' in self.base_url.lower() or 'esplora' in self.base_url.lower():
                # For testnet, use testnet API endpoint
                if use_testnet:
                    # Use testnet API - Blockstream format is /testnet/api
                    if '/testnet/api' not in self.base_url:
                        # Replace mainnet API with testnet
                        testnet_url = self.base_url.replace('/api', '/testnet/api')
                        if '/testnet/api' not in testnet_url:
                            # If no /api in URL, add /testnet/api
                            testnet_url = f"{self.base_url.rstrip('/')}/testnet/api"
                    else:
                        testnet_url = self.base_url
                    api_url = f"{testnet_url}/address/{address}/txs"
                else:
                    api_url = f"{self.base_url}/address/{address}/txs"
                
                logger.info(f"Checking {address} on {'testnet' if use_testnet else 'mainnet'} API: {api_url}")
                response = requests.get(api_url, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            else:
                # Generic API
                response = requests.get(
                    f"{self.base_url}/address/{address}/transactions",
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {e}")
            logger.error(f"  URL attempted: {api_url if 'api_url' in locals() else 'unknown'}")
            logger.error(f"  Network setting: {'testnet' if self.network.is_testnet else 'mainnet'}")
            logger.error(f"  Address format: {'testnet' if is_testnet_address else 'mainnet'}")
            return []
    
    def get_transaction(self, txid):
        """Get transaction details by hash"""
        try:
            response = requests.get(f"{self.base_url}/tx/{txid}", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting transaction {txid}: {e}")
            return None
    
    def inspect_transaction_for_address(self, txid, address):
        """
        Inspect a transaction and return total sats received by address,
        confirmation status, and block height.
        """
        tx = self.get_transaction(txid)
        if not tx:
            return 0, False, None
        
        # Calculate total received by this address
        total_received = 0
        
        if 'blockstream' in self.base_url.lower():
            # Blockstream Esplora format
            for vout in tx.get('vout', []):
                scriptpubkey_address = vout.get('scriptpubkey_address')
                if scriptpubkey_address == address:
                    total_received += vout.get('value', 0)
            
            status = tx.get('status', {})
            confirmed = status.get('confirmed', False)
            block_height = status.get('block_height')
        else:
            # Generic format - adapt as needed
            for output in tx.get('outputs', []):
                if output.get('address') == address:
                    total_received += output.get('value', 0)
            
            confirmed = tx.get('confirmed', False)
            block_height = tx.get('block_height')
        
        return total_received, confirmed, block_height
    
    def compute_confirmations(self, tx_block_height):
        """Compute number of confirmations for a transaction"""
        if tx_block_height is None:
            return 0
        
        current_height = self.get_current_block_height()
        if current_height is None:
            return 0
        
        return max(0, current_height - tx_block_height + 1)
    
    def check_deposit_address(self, deposit_address, topup_intent=None):
        """
        Check a deposit address for incoming transactions.
        Updates TopUpIntent and creates OnChainTransaction records.
        
        Returns:
            bool: True if transaction found and processed
        """
        from .models import OnChainTransaction, TopUpIntent
        
        address = deposit_address.address
        network = deposit_address.network
        
        # In test mode, simulate deposits for testing (only for mainnet)
        # For testnet, always check real blockchain even in test mode
        # Use effective_is_testnet to respect WALLET_TEST_MODE
        if getattr(settings, 'WALLET_TEST_MODE', False) and not network.effective_is_testnet:
            return self._simulate_test_deposit(deposit_address, topup_intent)
        
        # Get transactions for this address
        txs = self.get_address_transactions(address)
        
        if not txs:
            return False
        
        # First, update existing pending transactions with new confirmation counts
        self._update_pending_transactions(deposit_address)
        
        # Process each transaction
        found_transaction = False
        
        for tx_data in txs:
            txid = tx_data.get('txid') or tx_data.get('hash')
            if not txid:
                continue
            
            # Check if we already processed this transaction
            existing_tx = OnChainTransaction.objects.filter(tx_hash=txid).first()
            if existing_tx:
                # Update existing transaction with latest data
                self._update_existing_transaction(existing_tx, tx_data, address, topup_intent)
                found_transaction = True
                continue
            
            # Inspect transaction
            total_received, confirmed, block_height = self.inspect_transaction_for_address(txid, address)
            
            if total_received == 0:
                continue
            
            # Calculate confirmations
            confirmations = 0
            if confirmed and block_height is not None:
                confirmations = self.compute_confirmations(block_height)
            
            # Convert to USD minor units using exchange rate API
            from .exchange_rates import convert_crypto_to_usd
            amount_minor = convert_crypto_to_usd(
                total_received,
                network.native_symbol,
                network.decimals
            )
            
            # Determine status
            required_conf = network.required_confirmations
            if confirmations >= required_conf:
                status = 'confirmed'
            elif confirmed:
                status = 'pending'  # Confirmed but not enough confirmations
            else:
                status = 'pending'
            
            # Get occurred_at from transaction
            occurred_at = timezone.now()
            if 'block_time' in tx_data:
                from datetime import datetime
                occurred_at = datetime.fromtimestamp(tx_data['block_time'])
            
            # Create OnChainTransaction
            onchain_tx = OnChainTransaction.objects.create(
                user=deposit_address.user,
                network=network,
                tx_hash=txid,
                from_address=tx_data.get('vin', [{}])[0].get('prevout', {}).get('scriptpubkey_address', 'unknown'),
                to_address=address,
                amount_atomic=total_received,
                amount_minor=amount_minor,
                confirmations=confirmations,
                required_confirmations=required_conf,
                status=status,
                occurred_at=occurred_at,
                raw=tx_data,
                topup_intent=topup_intent
            )
            
            # Update TopUpIntent if provided and amount matches
            if topup_intent and status == 'confirmed':
                # Process the confirmed transaction (credits wallet, creates transaction record)
                self._process_confirmed_transaction(onchain_tx)
            
            found_transaction = True
        
        return found_transaction
    
    def _update_pending_transactions(self, deposit_address):
        """
        Update existing pending transactions for this deposit address with new confirmation counts.
        This ensures transactions that were pending get updated as confirmations increase.
        """
        from .models import OnChainTransaction
        
        # Get all pending transactions for this address
        pending_txs = OnChainTransaction.objects.filter(
            to_address=deposit_address.address,
            status='pending',
            network=deposit_address.network
        )
        
        for pending_tx in pending_txs:
            try:
                # Get latest transaction data from blockchain
                tx_data = self.get_transaction(pending_tx.tx_hash)
                if not tx_data:
                    continue
                
                # Update confirmations
                status = tx_data.get('status', {})
                confirmed = status.get('confirmed', False)
                block_height = status.get('block_height')
                
                if confirmed and block_height is not None:
                    confirmations = self.compute_confirmations(block_height)
                    pending_tx.confirmations = confirmations
                    pending_tx.updated_at = timezone.now()
                    
                    # Update status if enough confirmations
                    if confirmations >= pending_tx.required_confirmations:
                        pending_tx.status = 'confirmed'
                        logger.info(f"Transaction {pending_tx.tx_hash[:20]}... confirmed with {confirmations} confirmations")
                        
                        # Process the confirmed transaction
                        self._process_confirmed_transaction(pending_tx)
                    else:
                        logger.debug(f"Transaction {pending_tx.tx_hash[:20]}... has {confirmations}/{pending_tx.required_confirmations} confirmations")
                    
                    pending_tx.save()
            except Exception as e:
                logger.error(f"Error updating pending transaction {pending_tx.tx_hash[:20]}...: {e}")
    
    def _update_existing_transaction(self, existing_tx, tx_data, address, topup_intent):
        """
        Update an existing transaction with latest blockchain data.
        """
        # Inspect transaction for latest data
        total_received, confirmed, block_height = self.inspect_transaction_for_address(existing_tx.tx_hash, address)
        
        # Update confirmations
        if confirmed and block_height is not None:
            confirmations = self.compute_confirmations(block_height)
            existing_tx.confirmations = confirmations
            existing_tx.updated_at = timezone.now()
            
            # Update status if enough confirmations
            if confirmations >= existing_tx.required_confirmations and existing_tx.status != 'confirmed':
                existing_tx.status = 'confirmed'
                logger.info(f"Transaction {existing_tx.tx_hash[:20]}... confirmed with {confirmations} confirmations")
                
                # Process the confirmed transaction
                self._process_confirmed_transaction(existing_tx)
            
            existing_tx.save()
    
    def _process_confirmed_transaction(self, onchain_tx):
        """
        Process a confirmed transaction: update top-up intent, trigger sweep, credit wallet after sweep confirmation.
        """
        from .models import TopUpIntent, Wallet
        from transactions.models import Transaction
        from .sweep_service import SweepService
        
        # Get the top-up intent if it exists
        topup_intent = onchain_tx.topup_intent
        
        # Check if amount matches (within 1% tolerance) if topup_intent exists
        if topup_intent:
            expected_minor = topup_intent.amount_minor
            amount_minor = onchain_tx.amount_minor
            
            if abs(amount_minor - expected_minor) / expected_minor > 0.01:
                logger.warning(f"Amount mismatch for top-up {topup_intent.id}: expected ${expected_minor/100:.2f}, got ${amount_minor/100:.2f}")
                return
            
            # Update top-up intent
            if topup_intent.status != 'succeeded':
                topup_intent.status = 'succeeded'
                topup_intent.save()
                logger.info(f"Top-up intent {topup_intent.id} marked as succeeded")
        
        # Check if already swept
        if hasattr(onchain_tx, 'sweep_transaction'):
            sweep_tx = onchain_tx.sweep_transaction
            # If sweep is confirmed, credit wallet
            if sweep_tx.status == 'confirmed':
                self._credit_wallet_after_sweep(onchain_tx, sweep_tx)
            else:
                logger.info(f"Sweep {sweep_tx.id} for transaction {onchain_tx.tx_hash} is {sweep_tx.status}, waiting for confirmation")
            return
        
        # Trigger sweep to hot wallet
        try:
            sweep_service = SweepService()
            sweep_tx = sweep_service.sweep_deposit(onchain_tx)
            logger.info(f"Triggered sweep {sweep_tx.id} for transaction {onchain_tx.tx_hash}")
            
            # If sweep is immediately confirmed (unlikely but possible), credit wallet
            if sweep_tx.status == 'confirmed':
                self._credit_wallet_after_sweep(onchain_tx, sweep_tx)
            else:
                logger.info(f"Sweep {sweep_tx.id} broadcast, waiting for confirmation before crediting wallet")
                
        except Exception as e:
            logger.error(f"Failed to sweep deposit for transaction {onchain_tx.tx_hash}: {e}")
            # Don't credit wallet if sweep fails - funds are still in user address
            # Admin can manually retry sweep later
    
    def _credit_wallet_after_sweep(self, onchain_tx, sweep_tx):
        """
        Credit user wallet after sweep is confirmed.
        This ensures funds are in hot wallet before crediting user.
        """
        from .models import Wallet
        from transactions.models import Transaction
        
        # All fields are now MoneyField - use dollars directly
        amount = onchain_tx.amount_minor  # MoneyField
        
        # Credit user's wallet
        wallet, _ = Wallet.objects.get_or_create(
            user=onchain_tx.user,
            defaults={'currency_code': 'USD', 'balance_minor': 0}
        )
        
        # Only credit if not already credited (check if transaction record exists)
        if not Transaction.objects.filter(related_onchain_tx_id=onchain_tx.id).exists():
            wallet.balance_minor += amount.amount
            wallet.save()
            logger.info(f"Credited ${amount.amount:.2f} to wallet for user {onchain_tx.user.email} after sweep confirmation")
            
            # Create transaction record with sweep tx hash - all MoneyFields now
            Transaction.objects.create(
                user=onchain_tx.user,
                direction='credit',
                category='topup',
                amount_minor=amount.amount,
                currency_code='USD',
                description=f'Crypto deposit via {onchain_tx.network.name}',
                balance_after_minor=wallet.balance_minor.amount,
                status='completed',
                related_topup_intent_id=onchain_tx.topup_intent.id if onchain_tx.topup_intent else None,
                related_onchain_tx_id=onchain_tx.id,
                sweep_tx_hash=sweep_tx.tx_hash,
            )
            logger.info(f"Created transaction record for on-chain transaction {onchain_tx.id} with sweep {sweep_tx.tx_hash}")
    
    def _simulate_test_deposit(self, deposit_address, topup_intent=None):
        """
        Simulate a deposit in test mode for development/testing.
        This allows testing the wallet flow without real blockchain transactions.
        """
        from .models import OnChainTransaction, TopUpIntent, Wallet
        from transactions.models import Transaction
        
        # Only simulate if there's a pending top-up intent
        if not topup_intent or topup_intent.status != 'pending':
            return False
        
        # Check if we already simulated this
        if OnChainTransaction.objects.filter(
            topup_intent=topup_intent,
            status='confirmed'
        ).exists():
            return False
        
        # Simulate transaction after a short delay (in real scenario, this would be immediate)
        # For now, we'll create a simulated transaction
        from .exchange_rates import convert_crypto_to_usd
        
        # Simulate receiving the expected amount in crypto
        # topup_intent.amount_minor is now MoneyField (dollars)
        expected_usd = float(topup_intent.amount_minor.amount)
        # Use a rough rate to calculate crypto amount (this is just for simulation)
        if topup_intent.network.native_symbol.upper() == 'BTC':
            simulated_crypto_atomic = int(expected_usd / 50000 * 1e8)  # Rough BTC rate
        elif topup_intent.network.native_symbol.upper() in ['ETH', 'ETHEREUM']:
            simulated_crypto_atomic = int(expected_usd / 3000 * 1e18)  # Rough ETH rate
        else:
            simulated_crypto_atomic = int(expected_usd * 100)  # Default
        
        # Create simulated on-chain transaction
        onchain_tx = OnChainTransaction.objects.create(
            user=deposit_address.user,
            network=topup_intent.network,
            tx_hash=f"test_tx_{topup_intent.id}_{timezone.now().timestamp()}",
            from_address="test_sender_address",
            to_address=deposit_address.address,
            amount_atomic=simulated_crypto_atomic,
            amount_minor=topup_intent.amount_minor,
            confirmations=topup_intent.network.required_confirmations,
            required_confirmations=topup_intent.network.required_confirmations,
            status='confirmed',
            occurred_at=timezone.now(),
            raw={'test_mode': True},
            topup_intent=topup_intent
        )
        
        # Update top-up intent
        topup_intent.status = 'succeeded'
        topup_intent.save()
        
        # Credit user's wallet - all fields are MoneyField (dollars)
        wallet, _ = Wallet.objects.get_or_create(
            user=deposit_address.user,
            defaults={'currency_code': 'USD', 'balance_minor': 0}
        )
        wallet.balance_minor += topup_intent.amount_minor.amount
        wallet.save()
        
        # Create transaction record - all MoneyFields now
        Transaction.objects.create(
            user=deposit_address.user,
            direction='credit',
            category='topup',
            amount_minor=topup_intent.amount_minor.amount,
            currency_code='USD',
            description=f'Crypto deposit via {topup_intent.network.name} (Test Mode)',
            balance_after_minor=wallet.balance_minor.amount,
            status='completed',
            related_topup_intent_id=topup_intent.id,
            related_onchain_tx_id=onchain_tx.id,
        )
        
        logger.info(f"Simulated deposit for top-up {topup_intent.id} in test mode")
        return True

