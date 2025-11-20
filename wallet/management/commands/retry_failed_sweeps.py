"""
Management command to retry failed sweep transactions.
This should be run periodically (e.g., every hour) to retry failed sweeps.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

from django.db import models
from wallet.models import SweepTransaction, ConsolidationTransaction
from wallet.sweep_service import SweepService
from wallet.hot_wallet_manager import HotWalletManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retry failed sweep and consolidation transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--network',
            type=str,
            help='Network key to process (e.g., btc). If not specified, processes all networks.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of failed transactions to retry (default: 20)',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['sweep', 'consolidation', 'both'],
            default='both',
            help='Type of transactions to retry (default: both)',
        )

    def handle(self, *args, **options):
        network_key = options.get('network')
        limit = options.get('limit', 20)
        tx_type = options.get('type', 'both')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Retry Failed Transactions Command'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        total_retried = 0
        total_succeeded = 0
        total_failed = 0

        sweep_service = SweepService()
        consolidation_manager = HotWalletManager()

        # Retry failed sweeps
        if tx_type in ['sweep', 'both']:
            self.stdout.write('\nRetrying failed sweeps...')

            failed_sweeps = SweepTransaction.objects.filter(
                status='failed',
                retry_count__lt=models.F('max_retries')
            )

            if network_key:
                failed_sweeps = failed_sweeps.filter(network__key=network_key)

            failed_sweeps = failed_sweeps.select_related('network', 'user', 'onchain_tx')[:limit]

            for sweep_tx in failed_sweeps:
                total_retried += 1
                tx_short = sweep_tx.tx_hash[:20] if sweep_tx.tx_hash else sweep_tx.id

                try:
                    retried = sweep_service.retry_failed_sweep(sweep_tx)

                    if retried.status == 'failed':
                        total_failed += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Retry failed for sweep {tx_short}...: {retried.error_message}'
                            )
                        )
                    else:
                        total_succeeded += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Retry succeeded for sweep {tx_short}... → '
                                f'{retried.tx_hash[:20] if retried.tx_hash else "pending"}...'
                            )
                        )

                except Exception as e:
                    total_failed += 1
                    logger.error(f"Error retrying sweep {sweep_tx.id}: {e}", exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error retrying sweep {tx_short}...: {e}')
                    )

        # Retry failed consolidations
        if tx_type in ['consolidation', 'both']:
            self.stdout.write('\nRetrying failed consolidations...')

            failed_consolidations = ConsolidationTransaction.objects.filter(
                status='failed',
                retry_count__lt=models.F('max_retries')
            )

            if network_key:
                failed_consolidations = failed_consolidations.filter(network__key=network_key)

            failed_consolidations = failed_consolidations.select_related('network', 'hot_wallet', 'cold_wallet')[:limit]

            for consolidation_tx in failed_consolidations:
                total_retried += 1
                tx_short = consolidation_tx.tx_hash[:20] if consolidation_tx.tx_hash else consolidation_tx.id

                try:
                    retried = consolidation_manager.retry_failed_consolidation(consolidation_tx)

                    if retried.status == 'failed':
                        total_failed += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Retry failed for consolidation {tx_short}...: {retried.error_message}'
                            )
                        )
                    else:
                        total_succeeded += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Retry succeeded for consolidation {tx_short}... → '
                                f'{retried.tx_hash[:20] if retried.tx_hash else "pending"}...'
                            )
                        )

                except Exception as e:
                    total_failed += 1
                    logger.error(f"Error retrying consolidation {consolidation_tx.id}: {e}", exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error retrying consolidation {tx_short}...: {e}')
                    )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 60}\n'
                f'Retry Summary:\n'
                f'  Transactions retried: {total_retried}\n'
                f'  Succeeded: {total_succeeded}\n'
                f'  Failed: {total_failed}\n'
                f'{"=" * 60}'
            )
        )

