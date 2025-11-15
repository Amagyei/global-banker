from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Wallet, CryptoNetwork, DepositAddress, TopUpIntent, AddressIndex

User = get_user_model()


class WalletTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        self.network = CryptoNetwork.objects.create(
            key='btc',
            name='Bitcoin Testnet',
            native_symbol='BTC',
            decimals=8,
            explorer_url='https://blockstream.info/testnet',
            explorer_api_url='https://blockstream.info/testnet/api',
            is_testnet=True,
            is_active=True,
            required_confirmations=2,
        )

    def test_get_wallet(self):
        """Test getting user wallet"""
        self.client.force_authenticate(user=self.user)
        url = reverse('wallet-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('balance', res.data[0])
        self.assertEqual(res.data[0]['currency_code'], 'USD')

    def test_wallet_auto_creation(self):
        """Test that wallet is auto-created on first access"""
        self.client.force_authenticate(user=self.user)
        url = reverse('wallet-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # Verify wallet was created
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance_minor, 0)
        self.assertEqual(wallet.currency_code, 'USD')

    def test_get_networks(self):
        """Test getting crypto networks"""
        self.client.force_authenticate(user=self.user)
        url = reverse('network-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreater(len(res.data), 0)

    def test_create_topup(self):
        """Test creating a top-up intent"""
        self.client.force_authenticate(user=self.user)
        url = reverse('topup-list')
        data = {
            'amount_minor': 5000,  # $50.00
            'network_id': str(self.network.id),
            'ttl_minutes': 30,
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['amount_minor'], 5000)
        self.assertIn('deposit_address', res.data)
        self.assertIn('address', res.data['deposit_address'])

    def test_topup_creates_deposit_address(self):
        """Test that top-up creates a deposit address"""
        self.client.force_authenticate(user=self.user)
        url = reverse('topup-list')
        data = {
            'amount_minor': 5000,
            'network_id': str(self.network.id),
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Verify deposit address was created
        deposit_address = DepositAddress.objects.filter(
            user=self.user,
            network=self.network
        ).first()
        self.assertIsNotNone(deposit_address)
        self.assertTrue(deposit_address.is_active)

    def test_topup_reuses_deposit_address(self):
        """Test that subsequent top-ups reuse the same address"""
        self.client.force_authenticate(user=self.user)
        url = reverse('topup-list')
        data = {
            'amount_minor': 5000,
            'network_id': str(self.network.id),
        }
        
        # Create first top-up
        res1 = self.client.post(url, data, format='json')
        address1 = res1.data['deposit_address']['address']
        
        # Create second top-up
        res2 = self.client.post(url, data, format='json')
        address2 = res2.data['deposit_address']['address']
        
        # Should reuse same address
        self.assertEqual(address1, address2)

    def test_get_topups(self):
        """Test getting user's top-ups"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.client.force_authenticate(user=self.user)
        
        # Create a top-up
        TopUpIntent.objects.create(
            user=self.user,
            amount_minor=5000,
            currency_code='USD',
            network=self.network,
            deposit_address=DepositAddress.objects.create(
                user=self.user,
                network=self.network,
                address='test_address_123',
                index=0,
            ),
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        
        url = reverse('topup-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['amount_minor'], 5000)

    def test_address_index_atomic(self):
        """Test that address index reservation is atomic"""
        from wallet.utils import reserve_next_index
        
        # Reserve multiple indices
        idx1 = reserve_next_index('test')
        idx2 = reserve_next_index('test')
        idx3 = reserve_next_index('test')
        
        self.assertEqual(idx1, 0)
        self.assertEqual(idx2, 1)
        self.assertEqual(idx3, 2)
        
        # Verify in database
        index_obj = AddressIndex.objects.get(name='test')
        self.assertEqual(index_obj.next_index, 3)
