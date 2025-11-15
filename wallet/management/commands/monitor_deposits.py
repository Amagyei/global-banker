"""
Management command to monitor deposit addresses for incoming transactions.
Run this periodically (e.g., every 5 minutes via cron or Celery).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from wallet.models import CryptoNetwork, DepositAddress, TopUpIntent
from wallet.blockchain import BlockchainMonitor


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

    def handle(self, *args, **options):
        network_key = options.get('network')
        specific_address = options.get('address')
        
        # Get networks to monitor
        if network_key:
            networks = CryptoNetwork.objects.filter(key=network_key, is_active=True)
        else:
            networks = CryptoNetwork.objects.filter(is_active=True)
        
        if not networks.exists():
            self.stdout.write(self.style.WARNING('No active networks found'))
            return
        
        total_checked = 0
        total_found = 0
        
        for network in networks:
            self.stdout.write(f'Monitoring {network.name} ({network.key})...')
            
            # Get addresses to monitor
            if specific_address:
                addresses = DepositAddress.objects.filter(
                    address=specific_address,
                    network=network,
                    is_active=True
                )
            else:
                # Get active addresses with pending top-ups
                addresses = DepositAddress.objects.filter(
                    network=network,
                    is_active=True,
                    topup_intents__status__in=['pending', 'awaiting_confirmations']
                ).distinct()
            
            monitor = BlockchainMonitor(network)
            
            for deposit_address in addresses:
                total_checked += 1
                
                # Get pending top-up intent for this address
                topup = TopUpIntent.objects.filter(
                    deposit_address=deposit_address,
                    status__in=['pending', 'awaiting_confirmations']
                ).first()
                
                try:
                    found = monitor.check_deposit_address(deposit_address, topup)
                    if found:
                        total_found += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Found transaction for {deposit_address.address[:20]}...'
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error checking {deposit_address.address[:20]}...: {e}'
                        )
                    )
        
        # Check for expired top-ups
        expired = TopUpIntent.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        )
        expired_count = expired.update(status='expired')
        
        if expired_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Marked {expired_count} expired top-up intents')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted: Checked {total_checked} addresses, found {total_found} transactions'
            )
        )

