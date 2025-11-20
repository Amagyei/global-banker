"""
Management command to monitor deposit addresses for incoming transactions.
Run this periodically (e.g., every 5 minutes via cron or Celery).

Enhanced with robust error handling, retries, and health checks.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from wallet.models import CryptoNetwork, DepositAddress, TopUpIntent, OnChainTransaction
from wallet.blockchain import BlockchainMonitor
from wallet.monitoring import RobustBlockchainMonitor, MonitoringError, APIError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor deposit addresses for incoming cryptocurrency transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--network',
            type=str,
            help='Network key to monitor (e.g., btc, eth). If not provided, monitors all active networks.',
        )
        parser.add_argument(
            '--address',
            type=str,
            help='Specific address to monitor (optional)',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run health check on all networks before monitoring',
        )
        parser.add_argument(
            '--skip-healthy',
            action='store_true',
            help='Skip networks that fail health check',
        )
        parser.add_argument(
            '--update-pending',
            action='store_true',
            help='Update existing pending transactions (default: True)',
            default=True,
        )

    def handle(self, *args, **options):
        network_key = options.get('network')
        specific_address = options.get('address')
        health_check = options.get('health_check', False)
        skip_healthy = options.get('skip_healthy', False)
        update_pending = options.get('update_pending', True)
        
        # Get networks to monitor
        if network_key:
            networks = CryptoNetwork.objects.filter(key=network_key, is_active=True)
        else:
            networks = CryptoNetwork.objects.filter(is_active=True)
        
        if not networks.exists():
            self.stdout.write(self.style.WARNING('No active networks found'))
            return
        
        # Health check if requested
        if health_check:
            self.stdout.write('Running health checks...')
            healthy_networks = []
            for network in networks:
                robust_monitor = RobustBlockchainMonitor(network)
                is_healthy, message = robust_monitor.health_check()
                if is_healthy:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {network.name}: {message}'))
                    healthy_networks.append(network)
                else:
                    self.stdout.write(self.style.WARNING(f'  ✗ {network.name}: {message}'))
                    if not skip_healthy:
                        healthy_networks.append(network)  # Still monitor if not skipping
            
            if skip_healthy:
                networks = networks.filter(id__in=[n.id for n in healthy_networks])
                if not networks.exists():
                    self.stdout.write(self.style.ERROR('No healthy networks to monitor'))
                    return
        
        total_checked = 0
        total_found = 0
        total_errors = 0
        total_updated = 0
        
        for network in networks:
            self.stdout.write(f'\nMonitoring {network.name} ({network.key})...')
            net_type = 'testnet' if network.effective_is_testnet else 'mainnet'
            self.stdout.write(f'  Network type: {net_type}')
            
            # Get addresses to monitor
            if specific_address:
                addresses = DepositAddress.objects.filter(
                    address=specific_address,
                    network=network,
                    is_active=True
                )
            else:
                # Get active addresses with pending top-ups OR addresses with pending transactions
                addresses = DepositAddress.objects.filter(
                    network=network,
                    is_active=True
                ).filter(
                    # Has pending top-ups OR has pending on-chain transactions
                    topup_intents__status='pending'
                ).distinct()
            
            if not addresses.exists():
                self.stdout.write('  No addresses to monitor')
                continue
            
            # Use robust monitor for better error handling
            robust_monitor = RobustBlockchainMonitor(network)
            # Also use original monitor for compatibility
            monitor = BlockchainMonitor(network)
            
            for deposit_address in addresses:
                total_checked += 1
                address_short = deposit_address.address[:20]
                
                try:
                    # Update pending transactions if requested
                    if update_pending:
                        updated = self._update_pending_transactions(
                            deposit_address, robust_monitor, monitor
                        )
                        if updated > 0:
                            total_updated += updated
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Updated {updated} pending transaction(s) for {address_short}...'
                                )
                            )
                    
                    # Get pending top-up intent for this address
                    topup = TopUpIntent.objects.filter(
                        deposit_address=deposit_address,
                        status='pending'
                    ).first()
                    
                    # Check for new transactions
                    found = monitor.check_deposit_address(deposit_address, topup)
                    if found:
                        total_found += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Found new transaction for {address_short}...'
                            )
                        )
                
                except MonitoringError as e:
                    total_errors += 1
                    logger.error(f"Monitoring error for {address_short}...: {e}", exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Monitoring error for {address_short}...: {e}'
                        )
                    )
                except Exception as e:
                    total_errors += 1
                    logger.error(f"Unexpected error for {address_short}...: {e}", exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Unexpected error for {address_short}...: {e}'
                        )
                    )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 60}\n'
                f'Monitoring Summary:\n'
                f'  Addresses checked: {total_checked}\n'
                f'  New transactions found: {total_found}\n'
                f'  Pending transactions updated: {total_updated}\n'
                f'  Errors: {total_errors}\n'
                f'{"=" * 60}'
            )
        )
    
    def _update_pending_transactions(self, deposit_address, robust_monitor, monitor):
        """
        Update existing pending transactions for a deposit address.
        Returns number of transactions updated.
        """
        from wallet.models import OnChainTransaction
        
        pending_txs = OnChainTransaction.objects.filter(
            to_address=deposit_address.address,
            status='pending',
            network=deposit_address.network
        )
        
        updated_count = 0
        
        for pending_tx in pending_txs:
            try:
                # Get latest transaction data from blockchain
                tx_data = robust_monitor.get_transaction(pending_tx.tx_hash)
                if not tx_data:
                    continue
                
                # Update confirmations
                status = tx_data.get('status', {})
                confirmed = status.get('confirmed', False)
                block_height = status.get('block_height')
                
                if confirmed and block_height is not None:
                    confirmations = robust_monitor.compute_confirmations(block_height)
                    
                    with transaction.atomic():
                        pending_tx.refresh_from_db()
                        if pending_tx.status == 'pending':  # Double-check status
                            pending_tx.confirmations = confirmations
                            pending_tx.updated_at = timezone.now()
                            
                            # Update status if enough confirmations
                            if confirmations >= pending_tx.required_confirmations:
                                pending_tx.status = 'confirmed'
                                logger.info(
                                    f"Transaction {pending_tx.tx_hash[:20]}... confirmed "
                                    f"with {confirmations} confirmations"
                                )
                                
                                # Process the confirmed transaction
                                self._process_confirmed_transaction(pending_tx, monitor)
                            else:
                                logger.debug(
                                    f"Transaction {pending_tx.tx_hash[:20]}... has "
                                    f"{confirmations}/{pending_tx.required_confirmations} confirmations"
                                )
                            
                            pending_tx.save()
                            updated_count += 1
            except Exception as e:
                logger.error(
                    f"Error updating pending transaction {pending_tx.tx_hash[:20]}...: {e}",
                    exc_info=True
                )
        
        return updated_count
    
    def _process_confirmed_transaction(self, onchain_tx, monitor):
        """
        Process a confirmed transaction: credit user wallet, update top-up intent, create transaction record.
        """
        from wallet.models import TopUpIntent, Wallet
        from transactions.models import Transaction
        
        try:
            # Refresh from database to ensure we have latest data
            onchain_tx.refresh_from_db()
            
            # Get the top-up intent if it exists
            topup_intent = onchain_tx.topup_intent
            if not topup_intent:
                logger.warning(
                    f"No top-up intent found for transaction {onchain_tx.tx_hash[:20]}... - skipping crediting"
                )
                return
            
            # Check if amount matches (within 1% tolerance)
            expected_minor = topup_intent.amount_minor
            amount_minor = onchain_tx.amount_minor
            
            if abs(amount_minor - expected_minor) / expected_minor > 0.01:
                logger.warning(
                    f"Amount mismatch for top-up {topup_intent.id}: "
                    f"expected ${expected_minor/100:.2f}, got ${amount_minor/100:.2f} - skipping crediting"
                )
                return
            
            # Update top-up intent status
            if topup_intent.status != 'succeeded':
                topup_intent.status = 'succeeded'
                topup_intent.save()
                logger.info(f"✅ Top-up intent {topup_intent.id} marked as succeeded")
            
            # Credit user's wallet (with duplicate prevention)
            wallet, _ = Wallet.objects.get_or_create(
                user=onchain_tx.user,
                defaults={'currency_code': 'USD', 'balance_minor': 0}
            )
            
            # Check if already credited (prevent double-crediting)
            if Transaction.objects.filter(related_onchain_tx_id=onchain_tx.id).exists():
                logger.info(
                    f"Transaction {onchain_tx.tx_hash[:20]}... already credited - skipping"
                )
                return
            
            # Credit the wallet
            with transaction.atomic():
                wallet.refresh_from_db()  # Get latest balance
                wallet.balance_minor += amount_minor
                wallet.save()
                logger.info(
                    f"💰 Credited ${amount_minor/100:.2f} to wallet for user {onchain_tx.user.email} "
                    f"(new balance: ${wallet.balance_minor/100:.2f})"
                )
                
                # Create transaction record
                Transaction.objects.create(
                    user=onchain_tx.user,
                    direction='credit',
                    category='topup',
                    amount_minor=amount_minor,
                    currency_code='USD',
                    description=f'Crypto deposit via {onchain_tx.network.name}',
                    balance_after_minor=wallet.balance_minor,
                    status='completed',
                    related_topup_intent_id=topup_intent.id,
                    related_onchain_tx_id=onchain_tx.id,
                )
                logger.info(
                    f"📝 Created transaction record for on-chain transaction {onchain_tx.id}"
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  💰 Credited ${amount_minor/100:.2f} to {onchain_tx.user.email}'
                    )
                )
        
        except Exception as e:
            logger.error(
                f"❌ Error processing confirmed transaction {onchain_tx.tx_hash[:20]}...: {e}",
                exc_info=True
            )
            self.stdout.write(
                self.style.ERROR(
                    f'  ✗ Error crediting wallet: {e}'
                )
            )
            raise

