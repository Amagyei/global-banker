"""
Management command to consolidate hot wallet funds to cold wallet.
This should be run periodically (e.g., daily) or when hot wallet balance exceeds threshold.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

from wallet.models import HotWallet, ColdWallet, CryptoNetwork, ConsolidationTransaction
from wallet.hot_wallet_manager import HotWalletManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Consolidate hot wallet funds to cold wallet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--network',
            type=str,
            help='Network key to process (e.g., btc). If not specified, processes all active networks.',
        )
        parser.add_argument(
            '--threshold',
            type=int,
            help='Minimum balance in atomic units to trigger consolidation (default: 0.01 BTC equivalent)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force consolidation regardless of threshold',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be consolidated without actually consolidating',
        )

    def handle(self, *args, **options):
        network_key = options.get('network')
        threshold = options.get('threshold')
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Hot Wallet Consolidation Command'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No transactions will be created'))

        # Get networks to process
        if network_key:
            networks = CryptoNetwork.objects.filter(key=network_key, is_active=True)
        else:
            networks = CryptoNetwork.objects.filter(is_active=True)

        if not networks.exists():
            self.stdout.write(self.style.ERROR('No active networks found'))
            return

        total_processed = 0
        total_consolidated = 0
        total_errors = 0

        manager = HotWalletManager()

        for network in networks:
            self.stdout.write(f'\nProcessing {network.name} ({network.key})...')

            # Get hot wallet for this network
            hot_wallet = HotWallet.objects.filter(
                network=network,
                is_active=True
            ).first()

            if not hot_wallet:
                self.stdout.write('  No active hot wallet found')
                continue

            # Get cold wallet
            cold_wallet = ColdWallet.objects.filter(
                network=network,
                is_active=True
            ).first()

            if not cold_wallet:
                self.stdout.write('  No active cold wallet found')
                continue

            total_processed += 1

            try:
                # Get current balance
                balance = manager._get_address_balance(hot_wallet.address, network)
                self.stdout.write(f'  Hot wallet balance: {balance} {network.native_symbol}')

                # Set default threshold if not provided
                if threshold is None:
                    if network.native_symbol.upper() == 'BTC':
                        threshold = 1000000  # 0.01 BTC in satoshis
                    else:
                        threshold = 10000000000000000  # 0.01 ETH in wei (rough estimate)

                # Check if balance exceeds threshold
                if not force and balance < threshold:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Balance {balance} below threshold {threshold}. Use --force to consolidate anyway.'
                        )
                    )
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would consolidate {balance} {network.native_symbol} '
                            f'from {hot_wallet.address[:20]}... to {cold_wallet.address[:20]}...'
                        )
                    )
                    total_consolidated += 1
                else:
                    # Perform consolidation
                    consolidation_tx = manager.consolidate_to_cold(
                        network=network,
                        threshold_atomic=threshold,
                        force=force
                    )

                    if consolidation_tx.status == 'failed':
                        total_errors += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed to consolidate: {consolidation_tx.error_message}'
                            )
                        )
                    else:
                        total_consolidated += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Consolidated {consolidation_tx.amount_atomic} {network.native_symbol} '
                                f'→ {consolidation_tx.tx_hash[:20] if consolidation_tx.tx_hash else "pending"}...'
                            )
                        )

            except Exception as e:
                total_errors += 1
                logger.error(f"Error consolidating hot wallet for {network.key}: {e}", exc_info=True)
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error consolidating: {e}')
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 60}\n'
                f'Consolidation Summary:\n'
                f'  Hot wallets processed: {total_processed}\n'
                f'  Successfully consolidated: {total_consolidated}\n'
                f'  Errors: {total_errors}\n'
                f'{"=" * 60}'
            )
        )

