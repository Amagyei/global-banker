"""
Integration tests for OXA Pay API endpoints
Tests actual API calls that the frontend makes
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
import json

from wallet.models import CryptoNetwork, OxaPayPayment, OxaPayStaticAddress

User = get_user_model()


class OxaPayTopUpAPITests(APITestCase):
    """Test OXA Pay top-up API endpoints (what frontend calls)"""
    
    def setUp(self):
        """Set up test user and networks"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create all supported networks
        self.networks = {}
        network_configs = [
            {'key': 'btc', 'name': 'Bitcoin', 'symbol': 'BTC', 'decimals': 8},
            {'key': 'eth', 'name': 'Ethereum', 'symbol': 'ETH', 'decimals': 18},
            {'key': 'usdt', 'name': 'Tether USD', 'symbol': 'USDT', 'decimals': 6},
            {'key': 'usdc', 'name': 'USD Coin', 'symbol': 'USDC', 'decimals': 6},
            {'key': 'bnb', 'name': 'Binance Coin', 'symbol': 'BNB', 'decimals': 18},
            {'key': 'sol', 'name': 'Solana', 'symbol': 'SOL', 'decimals': 9},
            {'key': 'ltc', 'name': 'Litecoin', 'symbol': 'LTC', 'decimals': 8},
        ]
        
        for config in network_configs:
            self.networks[config['key']] = CryptoNetwork.objects.create(
                key=config['key'],
                name=config['name'],
                native_symbol=config['symbol'],
                decimals=config['decimals'],
                is_testnet=False,
                is_active=True,
                explorer_url=f'https://explorer.example.com/{config["key"]}',
                explorer_api_url=f'https://api.explorer.example.com/{config["key"]}',
                required_confirmations=2
            )
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_btc_topup_via_api(self, mock_client_class):
        """Test creating BTC top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        # Mock OXA Pay client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock API response
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '123456789',
            'address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'qr_code': 'https://api.oxapay.com/qr/123456789',
            'amount': 10.0,
            'pay_amount': 0.00015,
            'pay_currency': 'btc',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        # Make API call
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 1000,  # $10.00
            'network_id': str(self.networks['btc'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('topup', response.data)
        self.assertIn('oxapay_payment', response.data)
        
        # Verify topup data
        topup = response.data['topup']
        self.assertEqual(topup['amount_minor'], 1000)
        self.assertEqual(topup['currency_code'], 'USD')
        self.assertIsNone(topup['deposit_address'])  # OXA Pay doesn't use deposit_address
        
        # Verify OXA Pay payment data
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['track_id'], '123456789')
        self.assertEqual(oxa_payment['address'], 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')
        self.assertEqual(float(oxa_payment['amount']), 10.0)  # Amount is Decimal, compare as float
        self.assertEqual(oxa_payment['pay_currency'], 'btc')
        
        # Verify API call was made correctly
        mock_client.generate_white_label_payment.assert_called_once()
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['amount'], 10.0)
        self.assertEqual(call_kwargs['pay_currency'], 'btc')
        self.assertEqual(call_kwargs['network'], 'Bitcoin Network')
        self.assertEqual(call_kwargs['currency'], 'usd')
        self.assertIsNone(call_kwargs.get('to_currency'))  # BTC is native coin, no to_currency
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_eth_topup_via_api(self, mock_client_class):
        """Test creating ETH top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '987654321',
            'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
            'qr_code': 'https://api.oxapay.com/qr/987654321',
            'amount': 25.0,
            'pay_amount': 0.0125,
            'pay_currency': 'eth',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 2500,  # $25.00
            'network_id': str(self.networks['eth'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['address'], '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb')
        self.assertTrue(oxa_payment['address'].startswith('0x'))
        
        # Verify network mapping
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['network'], 'Ethereum Network')
        self.assertEqual(call_kwargs['pay_currency'], 'eth')
        self.assertIsNone(call_kwargs.get('to_currency'))  # ETH is native coin
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_usdt_topup_via_api(self, mock_client_class):
        """Test creating USDT (TRON) top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '555555555',
            'address': 'TQn9YwB1Gp1X1g8qj1JpD7D6wLeEog395j',
            'qr_code': 'https://api.oxapay.com/qr/555555555',
            'amount': 50.0,
            'pay_amount': 50.0,
            'pay_currency': 'usdt',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 5000,  # $50.00
            'network_id': str(self.networks['usdt'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['address'], 'TQn9YwB1Gp1X1g8qj1JpD7D6wLeEog395j')
        self.assertTrue(oxa_payment['address'].startswith('T'))
        
        # Verify network mapping (USDT uses TRON)
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['network'], 'TRON')
        self.assertEqual(call_kwargs['pay_currency'], 'trx')  # USDT uses TRX as native coin
        self.assertEqual(call_kwargs['to_currency'], 'USDT')  # USDT is the token
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_usdc_topup_via_api(self, mock_client_class):
        """Test creating USDC (Ethereum) top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '444444444',
            'address': '0x8ba1f109551bD432803012645Hac136c22C1729',
            'qr_code': 'https://api.oxapay.com/qr/444444444',
            'amount': 100.0,
            'pay_amount': 100.0,
            'pay_currency': 'usdc',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 10000,  # $100.00
            'network_id': str(self.networks['usdc'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['address'], '0x8ba1f109551bD432803012645Hac136c22C1729')
        
        # Verify network mapping (USDC uses Ethereum Network)
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['network'], 'Ethereum Network')
        self.assertEqual(call_kwargs['pay_currency'], 'eth')  # USDC uses ETH as native coin
        self.assertEqual(call_kwargs['to_currency'], 'USDC')  # USDC is the token
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_bnb_topup_via_api(self, mock_client_class):
        """Test creating BNB (Binance Smart Chain) top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '333333333',
            'address': '0x1234567890abcdef1234567890abcdef12345678',
            'qr_code': 'https://api.oxapay.com/qr/333333333',
            'amount': 75.0,
            'pay_amount': 0.15,
            'pay_currency': 'bnb',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 7500,  # $75.00
            'network_id': str(self.networks['bnb'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['address'], '0x1234567890abcdef1234567890abcdef12345678')
        
        # Verify network mapping
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['network'], 'Binance Smart Chain')
        self.assertEqual(call_kwargs['pay_currency'], 'bnb')
        self.assertIsNone(call_kwargs.get('to_currency'))  # BNB is native coin
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_sol_topup_via_api(self, mock_client_class):
        """Test creating SOL (Solana) top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '222222222',
            'address': '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU',
            'qr_code': 'https://api.oxapay.com/qr/222222222',
            'amount': 200.0,
            'pay_amount': 1.5,
            'pay_currency': 'sol',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 20000,  # $200.00
            'network_id': str(self.networks['sol'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['address'], '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU')
        
        # Verify network mapping
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['network'], 'Solana Network')
        self.assertEqual(call_kwargs['pay_currency'], 'sol')
        self.assertIsNone(call_kwargs.get('to_currency'))  # SOL is native coin
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_ltc_topup_via_api(self, mock_client_class):
        """Test creating LTC (Litecoin) top-up via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_white_label_payment.return_value = {
            'track_id': '111111111',
            'address': 'LTC1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'qr_code': 'https://api.oxapay.com/qr/111111111',
            'amount': 30.0,
            'pay_amount': 0.25,
            'pay_currency': 'ltc',
            'currency': 'usd',
            'expired_at': 1734567890
        }
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 3000,  # $30.00
            'network_id': str(self.networks['ltc'].id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        oxa_payment = response.data['oxapay_payment']
        self.assertEqual(oxa_payment['address'], 'LTC1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')
        
        # Verify network mapping
        call_kwargs = mock_client.generate_white_label_payment.call_args[1]
        self.assertEqual(call_kwargs['network'], 'Litecoin Network')
        self.assertEqual(call_kwargs['pay_currency'], 'ltc')
        self.assertIsNone(call_kwargs.get('to_currency'))  # LTC is native coin
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_topup_without_authentication(self, mock_client_class):
        """Test that unauthenticated requests are rejected"""
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 1000,
            'network_id': str(self.networks['btc'].id),
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_topup_invalid_network(self, mock_client_class):
        """Test that invalid network ID returns 404"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': 1000,
            'network_id': '00000000-0000-0000-0000-000000000000',  # Invalid UUID
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_topup_invalid_amount(self, mock_client_class):
        """Test that invalid amount returns 400"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('topup-v2-list')
        data = {
            'amount_minor': -100,  # Negative amount
            'network_id': str(self.networks['btc'].id),
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_topup_missing_fields(self, mock_client_class):
        """Test that missing required fields return 400"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('topup-v2-list')
        
        # Missing network_id
        response = self.client.post(url, {'amount_minor': 1000}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing amount_minor
        response = self.client.post(url, {'network_id': str(self.networks['btc'].id)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OxaPayStaticAddressAPITests(APITestCase):
    """Test OXA Pay static address API endpoints"""
    
    def setUp(self):
        """Set up test user and networks"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        self.network = CryptoNetwork.objects.create(
            key='btc',
            name='Bitcoin',
            native_symbol='BTC',
            decimals=8,
            is_testnet=False,
            is_active=True,
            explorer_url='https://blockstream.info',
            explorer_api_url='https://blockstream.info/api',
            required_confirmations=2
        )
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_create_static_address_via_api(self, mock_client_class):
        """Test creating static address via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.generate_static_address.return_value = {
            'track_id': '999999999',
            'address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'qr_code': 'https://api.oxapay.com/qr/999999999',
            'network': 'Bitcoin Network',
            'currency': 'BTC'
        }
        
        url = reverse('oxapay-static-address-list')
        data = {
            'network_id': str(self.network.id),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['address'], 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')
        self.assertEqual(response.data['track_id'], '999999999')
        
        # Verify API call
        mock_client.generate_static_address.assert_called_once()
        call_kwargs = mock_client.generate_static_address.call_args[1]
        self.assertEqual(call_kwargs['network'], 'Bitcoin Network')
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_get_static_addresses_via_api(self, mock_client_class):
        """Test getting static addresses via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        # Create a static address
        OxaPayStaticAddress.objects.create(
            user=self.user,
            network=self.network,
            track_id='111111111',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            is_active=True
        )
        
        url = reverse('oxapay-static-address-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['address'], 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')


class OxaPayPaymentAPITests(APITestCase):
    """Test OXA Pay payment API endpoints"""
    
    def setUp(self):
        """Set up test user and payment"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        self.network = CryptoNetwork.objects.create(
            key='btc',
            name='Bitcoin',
            native_symbol='BTC',
            decimals=8,
            is_testnet=False,
            is_active=True,
            explorer_url='https://blockstream.info',
            explorer_api_url='https://blockstream.info/api',
            required_confirmations=2
        )
        
        self.payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='123456789',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            amount=10.0,
            pay_amount=0.00015,
            pay_currency='btc',
            currency='usd',
            status='pending'
        )
    
    def test_get_payments_via_api(self):
        """Test getting OXA Pay payments via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('oxapay-payment-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['track_id'], '123456789')
        self.assertEqual(response.data[0]['address'], 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')
    
    @patch('wallet.views_v2.OxaPayClient')
    def test_get_accepted_currencies_via_api(self, mock_client_class):
        """Test getting accepted currencies via API endpoint"""
        self.client.force_authenticate(user=self.user)
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.get_accepted_currencies.return_value = {
            'list': ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'LTC']
        }
        
        url = reverse('oxapay-payment-accepted-currencies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('list', response.data)
        self.assertIn('BTC', response.data['list'])

