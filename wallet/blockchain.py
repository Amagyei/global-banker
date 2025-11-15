"""
Blockchain monitoring and transaction verification using Blockstream Esplora API
"""
import requests
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class BlockchainMonitor:
    """Monitor blockchain for transactions using Blockstream Esplora API"""
    
    def __init__(self, network):
        self.network = network
        self.base_url = network.explorer_api_url.rstrip('/')
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
            print(f"Error getting block height: {e}")
            return None
    
    def get_address_transactions(self, address):
        """Get all transactions for an address"""
        try:
            if 'blockstream' in self.base_url.lower():
                # Blockstream Esplora API
                response = requests.get(
                    f"{self.base_url}/address/{address}/txs",
                    timeout=self.timeout
                )
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
            print(f"Error getting transactions for {address}: {e}")
            return []
    
    def get_transaction(self, txid):
        """Get transaction details by hash"""
        try:
            response = requests.get(f"{self.base_url}/tx/{txid}", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting transaction {txid}: {e}")
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
        
        # Get transactions for this address
        txs = self.get_address_transactions(address)
        
        if not txs:
            return False
        
        # Process each transaction
        found_transaction = False
        
        for tx_data in txs:
            txid = tx_data.get('txid') or tx_data.get('hash')
            if not txid:
                continue
            
            # Check if we already processed this transaction
            if OnChainTransaction.objects.filter(tx_hash=txid).exists():
                continue
            
            # Inspect transaction
            total_received, confirmed, block_height = self.inspect_transaction_for_address(txid, address)
            
            if total_received == 0:
                continue
            
            # Calculate confirmations
            confirmations = 0
            if confirmed and block_height is not None:
                confirmations = self.compute_confirmations(block_height)
            
            # Convert to minor units (assuming 1 sat = 0.0001 USD for BTC, adjust as needed)
            # This is a placeholder - you'd need real exchange rate API
            amount_minor = int(total_received * 0.0001 * 100)  # Rough conversion
            
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
                # Check if amount is sufficient (within 1% tolerance)
                expected_minor = topup_intent.amount_minor
                if abs(amount_minor - expected_minor) / expected_minor <= 0.01:
                    topup_intent.status = 'succeeded'
                    topup_intent.save()
                    
                    # Credit user's wallet
                    from .models import Wallet
                    wallet, _ = Wallet.objects.get_or_create(
                        user=deposit_address.user,
                        defaults={'currency_code': 'USD', 'balance_minor': 0}
                    )
                    wallet.balance_minor += amount_minor
                    wallet.save()
                    
                    # Create transaction record
                    from transactions.models import Transaction
                    Transaction.objects.create(
                        user=deposit_address.user,
                        direction='credit',
                        category='topup',
                        amount_minor=amount_minor,
                        currency_code='USD',
                        description=f'Crypto deposit via {network.name}',
                        balance_after_minor=wallet.balance_minor,
                        status='completed',
                        related_topup_intent_id=topup_intent.id,
                        related_onchain_tx_id=onchain_tx.id,
                    )
            
            found_transaction = True
        
        return found_transaction

