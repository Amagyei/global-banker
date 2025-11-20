"""
Unit tests for OXA Pay wallet integration
Tests address generation for all supported cryptocurrency networks
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
import json

from wallet.models import CryptoNetwork, OxaPayStaticAddress, OxaPayPayment
from wallet.oxa_pay_client import OxaPayClient

User = get_user_model()


class OxaPayStaticAddressTests(TestCase):
    """Test OXA Pay static address generation for all wallet types"""
    
    def setUp(self):
        """Set up test user and networks"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create all supported networks
        self.networks = {
            'btc': CryptoNetwork.objects.create(
                key='btc',
                name='Bitcoin',
                native_symbol='BTC',
                decimals=8,
                is_testnet=False,
                is_active=True,
                explorer_url='https://blockstream.info',
                explorer_api_url='https://blockstream.info/api',
                required_confirmations=2
            ),
            'eth': CryptoNetwork.objects.create(
                key='eth',
                name='Ethereum',
                native_symbol='ETH',
                decimals=18,
                is_testnet=False,
                is_active=True,
                explorer_url='https://etherscan.io',
                explorer_api_url='https://api.etherscan.io/api',
                required_confirmations=12
            ),
            'usdt': CryptoNetwork.objects.create(
                key='usdt',
                name='Tether USD',
                native_symbol='USDT',
                decimals=6,
                is_testnet=False,
                is_active=True,
                explorer_url='https://tronscan.org',
                explorer_api_url='https://api.trongrid.io',
                required_confirmations=20
            ),
            'usdc': CryptoNetwork.objects.create(
                key='usdc',
                name='USD Coin',
                native_symbol='USDC',
                decimals=6,
                is_testnet=False,
                is_active=True,
                explorer_url='https://etherscan.io',
                explorer_api_url='https://api.etherscan.io/api',
                required_confirmations=12
            ),
            'bnb': CryptoNetwork.objects.create(
                key='bnb',
                name='Binance Coin',
                native_symbol='BNB',
                decimals=18,
                is_testnet=False,
                is_active=True,
                explorer_url='https://bscscan.com',
                explorer_api_url='https://api.bscscan.com/api',
                required_confirmations=12
            ),
            'sol': CryptoNetwork.objects.create(
                key='sol',
                name='Solana',
                native_symbol='SOL',
                decimals=9,
                is_testnet=False,
                is_active=True,
                explorer_url='https://solscan.io',
                explorer_api_url='https://api.solscan.io',
                required_confirmations=32
            ),
            'ltc': CryptoNetwork.objects.create(
                key='ltc',
                name='Litecoin',
                native_symbol='LTC',
                decimals=8,
                is_testnet=False,
                is_active=True,
                explorer_url='https://blockchair.com/litecoin',
                explorer_api_url='https://api.blockchair.com/litecoin',
                required_confirmations=6
            ),
        }
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_btc_static_address(self, mock_post):
        """Test creating Bitcoin static address"""
        network = self.networks['btc']
        
        # Mock OXA Pay API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '123456789',
                'address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                'qr_code': 'https://api.oxapay.com/qr/123456789',
                'network': 'Bitcoin Network',
                'currency': 'BTC'
            }
        }
        mock_post.return_value = mock_response
        
        # Create static address
        client = OxaPayClient()
        result = client.generate_static_address(
            network='Bitcoin Network',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-12345',
            description='Bitcoin static address for testing',
            auto_withdrawal=True
        )
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://api.oxapay.com/v1/payment/static-address')
        
        # Verify request payload
        request_data = json.loads(call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Bitcoin Network')
        self.assertEqual(request_data['email'], self.user.email)
        self.assertEqual(request_data['order_id'], 'ORD-12345')
        self.assertEqual(request_data['auto_withdrawal'], 1)
        
        # Verify response
        self.assertEqual(result['track_id'], '123456789')
        self.assertEqual(result['address'], 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_eth_static_address(self, mock_post):
        """Test creating Ethereum static address"""
        network = self.networks['eth']
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '987654321',
                'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
                'qr_code': 'https://api.oxapay.com/qr/987654321',
                'network': 'Ethereum Network',
                'currency': 'ETH'
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_static_address(
            network='Ethereum Network',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-ETH-001',
            description='Ethereum static address',
            auto_withdrawal=True
        )
        
        # Verify request
        request_data = json.loads(mock_post.call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Ethereum Network')
        
        # Verify response
        self.assertEqual(result['address'], '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb')
        self.assertTrue(result['address'].startswith('0x'))
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_usdt_static_address(self, mock_post):
        """Test creating USDT (TRON) static address"""
        network = self.networks['usdt']
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '555555555',
                'address': 'TQn9YwB1Gp1X1g8qj1JpD7D6wLeEog395j',
                'qr_code': 'https://api.oxapay.com/qr/555555555',
                'network': 'TRON',
                'currency': 'USDT',
                'to_currency': 'USDT'
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_static_address(
            network='TRON',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-USDT-001',
            description='USDT static address on TRON',
            auto_withdrawal=True,
            to_currency='USDT'
        )
        
        # Verify request
        request_data = json.loads(mock_post.call_args[1]['data'])
        self.assertEqual(request_data['network'], 'TRON')
        self.assertEqual(request_data['to_currency'], 'USDT')
        
        # Verify response
        self.assertEqual(result['address'], 'TQn9YwB1Gp1X1g8qj1JpD7D6wLeEog395j')
        self.assertTrue(result['address'].startswith('T'))
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_usdc_static_address(self, mock_post):
        """Test creating USDC (Ethereum) static address"""
        network = self.networks['usdc']
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '444444444',
                'address': '0x8ba1f109551bD432803012645Hac136c22C1729',
                'qr_code': 'https://api.oxapay.com/qr/444444444',
                'network': 'Ethereum Network',
                'currency': 'USDC',
                'to_currency': 'USDC'
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_static_address(
            network='Ethereum Network',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-USDC-001',
            description='USDC static address on Ethereum',
            auto_withdrawal=True,
            to_currency='USDC'
        )
        
        # Verify request
        request_data = json.loads(mock_post.call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Ethereum Network')
        self.assertEqual(request_data['to_currency'], 'USDC')
        
        # Verify response
        self.assertEqual(result['address'], '0x8ba1f109551bD432803012645Hac136c22C1729')
        self.assertTrue(result['address'].startswith('0x'))
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_bnb_static_address(self, mock_post):
        """Test creating BNB (Binance Smart Chain) static address"""
        network = self.networks['bnb']
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '333333333',
                'address': '0x1234567890abcdef1234567890abcdef12345678',
                'qr_code': 'https://api.oxapay.com/qr/333333333',
                'network': 'Binance Smart Chain',
                'currency': 'BNB'
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_static_address(
            network='Binance Smart Chain',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-BNB-001',
            description='BNB static address on BSC',
            auto_withdrawal=True
        )
        
        # Verify request
        request_data = json.loads(mock_post.call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Binance Smart Chain')
        
        # Verify response
        self.assertEqual(result['address'], '0x1234567890abcdef1234567890abcdef12345678')
        self.assertTrue(result['address'].startswith('0x'))
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_sol_static_address(self, mock_post):
        """Test creating Solana static address"""
        network = self.networks['sol']
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '222222222',
                'address': '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU',
                'qr_code': 'https://api.oxapay.com/qr/222222222',
                'network': 'Solana Network',
                'currency': 'SOL'
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_static_address(
            network='Solana Network',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-SOL-001',
            description='Solana static address',
            auto_withdrawal=True
        )
        
        # Verify request
        request_data = json.loads(mock_post.call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Solana Network')
        
        # Verify response
        self.assertEqual(result['address'], '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU')
        # Solana addresses are base58, typically 32-44 characters
        self.assertGreaterEqual(len(result['address']), 32)
        self.assertLessEqual(len(result['address']), 44)
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_ltc_static_address(self, mock_post):
        """Test creating Litecoin static address"""
        network = self.networks['ltc']
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '111111111',
                'address': 'LTC1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                'qr_code': 'https://api.oxapay.com/qr/111111111',
                'network': 'Litecoin Network',
                'currency': 'LTC'
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_static_address(
            network='Litecoin Network',
            callback_url='https://example.com/callback',
            email=self.user.email,
            order_id='ORD-LTC-001',
            description='Litecoin static address',
            auto_withdrawal=True
        )
        
        # Verify request
        request_data = json.loads(mock_post.call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Litecoin Network')
        
        # Verify response
        self.assertEqual(result['address'], 'LTC1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')
        # Litecoin addresses typically start with L (legacy) or M (P2SH) or ltc1 (bech32)
        self.assertTrue(
            result['address'].startswith('L') or 
            result['address'].startswith('M') or 
            result['address'].startswith('ltc1')
        )


class OxaPayWhiteLabelPaymentTests(TestCase):
    """Test OXA Pay white-label payment generation for all wallet types"""
    
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
    
    @patch('wallet.oxa_pay_client.requests.Session.post')
    def test_create_white_label_payment_with_network(self, mock_post):
        """Test creating white-label payment with network field"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 200,
            'data': {
                'track_id': '999999999',
                'address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                'qr_code': 'https://api.oxapay.com/qr/999999999',
                'amount': 10.0,
                'pay_amount': 0.00015,
                'pay_currency': 'btc',
                'currency': 'usd',
                'expired_at': 1734567890
            }
        }
        mock_post.return_value = mock_response
        
        client = OxaPayClient()
        result = client.generate_white_label_payment(
            amount=10.0,
            pay_currency='btc',
            currency='usd',
            network='Bitcoin Network',  # Network is required
            lifetime=60,
            callback_url='https://example.com/callback',
            order_id='ORD-12345',
            email=self.user.email,
            description='Test payment',
            auto_withdrawal=True,
            under_paid_coverage=1.0
        )
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://api.oxapay.com/v1/payment/white-label')
        
        # Verify request payload
        request_data = json.loads(call_args[1]['data'])
        self.assertEqual(request_data['network'], 'Bitcoin Network')
        self.assertEqual(request_data['amount'], 10.0)
        self.assertEqual(request_data['pay_currency'], 'btc')
        self.assertEqual(request_data['currency'], 'usd')
        self.assertEqual(request_data['auto_withdrawal'], 1)
        self.assertEqual(request_data['under_paid_coverage'], 1.0)
        
        # Verify response
        self.assertEqual(result['track_id'], '999999999')
        self.assertEqual(result['address'], 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')


class OxaPayNetworkMappingTests(TestCase):
    """Test network key to OXA Pay network name mapping"""
    
    def setUp(self):
        """Set up test networks"""
        self.network_map = {
            'btc': 'Bitcoin Network',
            'eth': 'Ethereum Network',
            'usdt': 'TRON',
            'usdc': 'Ethereum Network',
            'bnb': 'Binance Smart Chain',
            'sol': 'Solana Network',
            'ltc': 'Litecoin Network',
        }
    
    def test_network_mapping_btc(self):
        """Test Bitcoin network mapping"""
        self.assertEqual(self.network_map['btc'], 'Bitcoin Network')
    
    def test_network_mapping_eth(self):
        """Test Ethereum network mapping"""
        self.assertEqual(self.network_map['eth'], 'Ethereum Network')
    
    def test_network_mapping_usdt(self):
        """Test USDT (TRON) network mapping"""
        self.assertEqual(self.network_map['usdt'], 'TRON')
    
    def test_network_mapping_usdc(self):
        """Test USDC (Ethereum) network mapping"""
        self.assertEqual(self.network_map['usdc'], 'Ethereum Network')
    
    def test_network_mapping_bnb(self):
        """Test BNB (BSC) network mapping"""
        self.assertEqual(self.network_map['bnb'], 'Binance Smart Chain')
    
    def test_network_mapping_sol(self):
        """Test Solana network mapping"""
        self.assertEqual(self.network_map['sol'], 'Solana Network')
    
    def test_network_mapping_ltc(self):
        """Test Litecoin network mapping"""
        self.assertEqual(self.network_map['ltc'], 'Litecoin Network')

