"""
Management command to sweep confirmed deposits to hot wallet.
This should be run periodically (e.g., every 5-10 minutes) to process confirmed deposits.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import logging

from wallet.models import OnChainTransaction, SweepTransaction, CryptoNetwork
from wallet.sweep_service import SweepService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sweep confirmed deposits from user addresses to hot wallet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--network',
            type=str,
            help='Network key to process (e.g., btc). If not specified, processes all active networks.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of deposits to process (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be swept without actually sweeping',
        )

    def handle(self, *args, **options):
        network_key = options.get('network')
        limit = options.get('limit', 50)
        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Sweep Deposits Command'))
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
        total_swept = 0
        total_errors = 0

        sweep_service = SweepService()

        for network in networks:
            self.stdout.write(f'\nProcessing {network.name} ({network.key})...')

            # Get confirmed on-chain transactions that haven't been swept yet
            confirmed_txs = OnChainTransaction.objects.filter(
                network=network,
                status='confirmed',
                sweep_transaction__isnull=True  # Not yet swept
            ).select_related('user', 'network', 'topup_intent')[:limit]

            if not confirmed_txs.exists():
                self.stdout.write('  No confirmed deposits to sweep')
                continue

            for onchain_tx in confirmed_txs:
                total_processed += 1
                tx_short = onchain_tx.tx_hash[:20]

                try:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [DRY RUN] Would sweep {tx_short}... '
                                f'({onchain_tx.amount_atomic} {network.native_symbol})'
                            )
                        )
                        total_swept += 1
                    else:
                        # Perform sweep
                        sweep_tx = sweep_service.sweep_deposit(onchain_tx)

                        if sweep_tx.status == 'failed':
                            total_errors += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ✗ Failed to sweep {tx_short}...: {sweep_tx.error_message}'
                                )
                            )
                        else:
                            total_swept += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Swept {tx_short}... → {sweep_tx.tx_hash[:20] if sweep_tx.tx_hash else "pending"}... '
                                    f'({sweep_tx.amount_atomic} {network.native_symbol})'
                                )
                            )

                except Exception as e:
                    total_errors += 1
                    logger.error(f"Error sweeping {onchain_tx.tx_hash}: {e}", exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error sweeping {tx_short}...: {e}')
                    )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 60}\n'
                f'Sweep Summary:\n'
                f'  Deposits processed: {total_processed}\n'
                f'  Successfully swept: {total_swept}\n'
                f'  Errors: {total_errors}\n'
                f'{"=" * 60}'
            )
        )

