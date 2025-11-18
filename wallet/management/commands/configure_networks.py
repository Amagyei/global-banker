"""
Django management command to configure networks based on WALLET_TEST_MODE.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from wallet.models import CryptoNetwork


class Command(BaseCommand):
    help = 'Configure networks based on WALLET_TEST_MODE setting'

    def handle(self, *args, **options):
        test_mode = getattr(settings, 'WALLET_TEST_MODE', False)
        
        self.stdout.write(f"WALLET_TEST_MODE: {test_mode}")
        self.stdout.write(f"Configuring networks to use {'testnet' if test_mode else 'mainnet'}...")
        
        # Update Bitcoin network
        btc_network = CryptoNetwork.objects.filter(key='btc').first()
        if btc_network:
            if test_mode and not btc_network.is_testnet:
                self.stdout.write(f"Updating Bitcoin network to testnet...")
                btc_network.is_testnet = True
                btc_network.explorer_api_url = 'https://blockstream.info/testnet/api'
                btc_network.explorer_url = 'https://blockstream.info/testnet'
                btc_network.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Bitcoin network updated to testnet"))
            elif not test_mode and btc_network.is_testnet:
                self.stdout.write(f"Updating Bitcoin network to mainnet...")
                btc_network.is_testnet = False
                btc_network.explorer_api_url = 'https://blockstream.info/api'
                btc_network.explorer_url = 'https://blockstream.info'
                btc_network.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Bitcoin network updated to mainnet"))
            else:
                self.stdout.write(f"Bitcoin network already configured correctly")
        else:
            self.stdout.write(self.style.WARNING("Bitcoin network not found in database"))
        
        self.stdout.write(self.style.SUCCESS("\n✅ Network configuration complete"))

