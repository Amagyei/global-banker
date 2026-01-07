"""
Tests for order updates when payments are validated via webhook.

This test suite verifies that:
1. Orders are updated from 'pending' to 'paid' when webhook confirms payment
2. Cart is cleared after payment confirmation
3. Transaction records are created correctly
4. Webhook is idempotent (can be called multiple times safely)
5. Both Account and FullzPackage orders are handled correctly

IMPORTANT: Before running these tests, ensure migrations have been applied:
    python manage.py makemigrations orders
    python manage.py migrate

Tests that use FullzPackage will be skipped if migrations haven't been run.
"""
import json
import hmac
import hashlib
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch, MagicMock
from orders.models import Order, OrderItem, Cart, CartItem
from catalog.models import Country, Bank, Account, FullzPackage
from wallet.models import Wallet, OxaPayPayment
from transactions.models import Transaction

User = get_user_model()


class OrderWebhookTests(TestCase):
    """Test order updates via OXA Pay webhook"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create catalog data
        self.us = Country.objects.create(
            code='US',
            name='United States',
            currency_code='USD',
            is_supported=True
        )
        self.chase = Bank.objects.create(
            name='Chase',
            country=self.us,
            is_active=True
        )
        self.account = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=100000,
            price_minor=9500,
            is_active=True
        )
        self.fullz_package = FullzPackage.objects.create(
            name='Starter Pack',
            description='10 fullz package',
            bank=self.chase,
            quantity=10,
            price_minor=2500,
            is_active=True
        )
        
        # Create wallet
        self.wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            balance_minor=0
        )
        
        # Create crypto network (required for OxaPayPayment)
        from wallet.models import CryptoNetwork
        self.network = CryptoNetwork.objects.create(
            key='btc',
            name='Bitcoin',
            native_symbol='BTC',
            decimals=8,
            explorer_url='https://blockstream.info',
            explorer_api_url='https://blockstream.info/api',
            is_testnet=False,
            is_active=True,
            required_confirmations=2
        )
        
        # Set up OXA Pay API key for HMAC signing
        self.api_key = 'test_api_key_12345'
        settings.OXAPAY_API_KEY = self.api_key
        
        self.client = Client()
    
    def _create_hmac_signature(self, body: str) -> str:
        """Create HMAC-SHA512 signature for webhook payload"""
        return hmac.new(
            self.api_key.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    def _create_webhook_payload(self, track_id: str, order_id: str, status: str = 'Paid', amount: float = 75.00) -> dict:
        """Create a webhook payload for testing"""
        return {
            'track_id': track_id,
            'status': status,
            'amount': amount,
            'value': amount,
            'sent_value': amount,
            'currency': 'USD',
            'order_id': order_id,
            'email': self.user.email,
            'type': 'invoice',
            'txs': [{
                'status': 'confirmed',
                'tx_hash': '0x1234567890abcdef',
                'sent_amount': amount,
                'received_amount': amount,
                'currency': 'USD',
                'network': 'Ethereum',
                'address': '0xabcdef1234567890',
                'confirmations': 12
            }]
        }
    
    def _send_webhook(self, payload: dict) -> dict:
        """Send webhook request with proper HMAC signature"""
        body = json.dumps(payload)
        signature = self._create_hmac_signature(body)
        
        # Use full path since webhook is in wallet.urls_v2 namespace
        response = self.client.post(
            '/api/v2/wallet/webhook/',
            data=body,
            content_type='application/json',
            HTTP_HMAC=signature
        )
        return response
    
    def test_webhook_updates_order_status_to_paid(self):
        """Test that webhook updates order status from 'pending' to 'paid'"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'OK')
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Verify payment status updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
    
    def test_webhook_clears_cart_after_payment(self):
        """Test that webhook clears user's cart after payment confirmation"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        
        # Create cart with items (simulating items that weren't cleared yet)
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        self.assertEqual(cart.items.count(), 1)
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify cart is cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)
    
    def test_webhook_creates_transaction_record(self):
        """Test that webhook creates a transaction record for order payment"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify transaction was created
        transaction = Transaction.objects.filter(
            related_order_id=order.id,
            user=self.user
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.direction, 'debit')
        self.assertEqual(transaction.category, 'purchase')
        self.assertEqual(transaction.status, 'completed')
        self.assertEqual(transaction.amount_minor, 9500)
        self.assertEqual(transaction.currency_code, 'USD')
        self.assertIn(order.order_number, transaction.description)
        self.assertIn('OXA Pay', transaction.description)
    
    def test_webhook_is_idempotent(self):
        """Test that webhook can be called multiple times without duplicating transactions"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook first time
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        response1 = self._send_webhook(payload)
        self.assertEqual(response1.status_code, 200)
        
        # Verify order is paid
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Count transactions
        transaction_count_before = Transaction.objects.filter(
            related_order_id=order.id
        ).count()
        
        # Send webhook second time (same payload)
        response2 = self._send_webhook(payload)
        self.assertEqual(response2.status_code, 200)
        
        # Verify order is still paid (not changed)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Verify no duplicate transaction created
        transaction_count_after = Transaction.objects.filter(
            related_order_id=order.id
        ).count()
        self.assertEqual(transaction_count_before, transaction_count_after)
    
    def test_webhook_handles_fullz_package_order(self):
        """Test that webhook correctly handles orders with FullzPackage items
        
        NOTE: This test requires migrations to be run first to add fullz_package_id column.
        Skip if migrations haven't been applied.
        """
        # Skip test if fullz_package_id column doesn't exist
        from django.db import connection
        columns = [col.name for col in connection.introspection.get_table_description(connection.cursor(), 'orders_orderitem')]
        if 'fullz_package_id' not in columns:
            self.skipTest("fullz_package_id column not found. Run migrations first: python manage.py migrate")
        
        # Create a pending order with FullzPackage
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=2500,
            fees_minor=0,
            total_minor=2500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=None,
            fullz_package=self.fullz_package,
            quantity=1,
            unit_price_minor=2500
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_456',
            order_id=order.order_number,
            amount=25.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_456',
            order_id=order.order_number,
            status='Paid',
            amount=25.00
        )
        response = self._send_webhook(payload)
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Verify transaction created
        transaction = Transaction.objects.filter(
            related_order_id=order.id
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount_minor, 2500)
    
    def test_webhook_handles_mixed_order(self):
        """Test that webhook handles orders with both Account and FullzPackage items
        
        NOTE: This test requires migrations to be run first to add fullz_package_id column.
        Skip if migrations haven't been applied.
        """
        # Skip test if fullz_package_id column doesn't exist
        from django.db import connection
        columns = [col.name for col in connection.introspection.get_table_description(connection.cursor(), 'orders_orderitem')]
        if 'fullz_package_id' not in columns:
            self.skipTest("fullz_package_id column not found. Run migrations first: python manage.py migrate")
        
        # Create a pending order with both types
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=12000,  # 95.00 + 25.00
            fees_minor=0,
            total_minor=12000,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            fullz_package=None,
            quantity=1,
            unit_price_minor=9500
        )
        OrderItem.objects.create(
            order=order,
            account=None,
            fullz_package=self.fullz_package,
            quantity=1,
            unit_price_minor=2500
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_789',
            order_id=order.order_number,
            amount=120.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_789',
            order_id=order.order_number,
            status='Paid',
            amount=120.00
        )
        response = self._send_webhook(payload)
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Verify both order items exist
        self.assertEqual(order.items.count(), 2)
        account_item = order.items.filter(account__isnull=False).first()
        package_item = order.items.filter(fullz_package__isnull=False).first()
        self.assertIsNotNone(account_item)
        self.assertIsNotNone(package_item)
    
    def test_webhook_rejects_invalid_hmac_signature(self):
        """Test that webhook rejects requests with invalid HMAC signature"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        
        # Send webhook with invalid signature
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        body = json.dumps(payload)
        invalid_signature = 'invalid_signature_12345'
        
        # Use full path since webhook is in wallet.urls_v2 namespace
        response = self.client.post(
            '/api/v2/wallet/webhook/',
            data=body,
            content_type='application/json',
            HTTP_HMAC=invalid_signature
        )
        
        # Verify request was rejected
        self.assertEqual(response.status_code, 400)
        
        # Verify order status NOT updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
    
    def test_webhook_handles_missing_order(self):
        """Test that webhook handles case where order doesn't exist"""
        # Create OxaPayPayment with non-existent order
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_999',
            order_id='ORD-2024-9999',  # Non-existent order
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_999',
            order_id='ORD-2024-9999',
            status='Paid',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Webhook should still return 200 (doesn't fail on missing order)
        # It just logs a warning and continues
        self.assertEqual(response.status_code, 200)
        
        # Payment status should still be updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
    
    def test_webhook_handles_already_paid_order(self):
        """Test that webhook handles order that's already paid"""
        # Create an already paid order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='paid'  # Already paid
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        
        # Count existing transactions
        transaction_count_before = Transaction.objects.filter(
            related_order_id=order.id
        ).count()
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify response is OK
        self.assertEqual(response.status_code, 200)
        
        # Verify order is still paid
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Verify no duplicate transaction created
        transaction_count_after = Transaction.objects.filter(
            related_order_id=order.id
        ).count()
        self.assertEqual(transaction_count_before, transaction_count_after)
    
    def test_webhook_handles_paying_status(self):
        """Test that webhook handles 'Paying' status (not yet paid)"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook with 'Paying' status
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Paying',  # Not yet paid
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify response is OK
        self.assertEqual(response.status_code, 200)
        
        # Verify order status NOT updated (still pending)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        
        # Verify payment status updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paying')
    
    def test_webhook_handles_failed_status(self):
        """Test that webhook handles 'Failed' status"""
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        
        # Create OxaPayPayment record
        payment = OxaPayPayment.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_123',
            order_id=order.order_number,
            amount=95.00,
            currency='USD',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            status='pending'
        )
        
        # Send webhook with 'Failed' status
        payload = self._create_webhook_payload(
            track_id='test_track_123',
            order_id=order.order_number,
            status='Failed',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify response is OK
        self.assertEqual(response.status_code, 200)
        
        # Verify order status NOT updated (still pending)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        
        # Verify payment status updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')
    
    def test_webhook_creates_payment_if_not_exists(self):
        """Test that webhook creates OxaPayPayment if it doesn't exist (via static address)"""
        from wallet.models import OxaPayStaticAddress
        
        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        
        # Create static address (webhook creates payment from static address if payment doesn't exist)
        static_address = OxaPayStaticAddress.objects.create(
            user=self.user,
            network=self.network,
            track_id='test_track_new',
            address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            order_id=order.order_number,
            email=self.user.email,
            description=f'Order {order.order_number}'
        )
        
        # Don't create payment record - webhook should create it from static address
        
        # Send webhook
        payload = self._create_webhook_payload(
            track_id='test_track_new',
            order_id=order.order_number,
            status='Paid',
            amount=95.00
        )
        response = self._send_webhook(payload)
        
        # Verify response is OK
        self.assertEqual(response.status_code, 200)
        
        # Verify payment was created
        payment = OxaPayPayment.objects.filter(
            track_id='test_track_new',
            user=self.user
        ).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, 'paid')
        self.assertEqual(payment.order_id, order.order_number)
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')


class OrderWebhookIntegrationTests(TestCase):
    """Integration tests for complete order-to-payment flow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create catalog
        self.us = Country.objects.create(
            code='US',
            name='United States',
            currency_code='USD',
            is_supported=True
        )
        self.chase = Bank.objects.create(
            name='Chase',
            country=self.us,
            is_active=True
        )
        self.account = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=100000,
            price_minor=9500,
            is_active=True
        )
        
        # Create wallet
        self.wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            balance_minor=0
        )
        
        # Create crypto network (required for OxaPayPayment)
        from wallet.models import CryptoNetwork
        self.network = CryptoNetwork.objects.create(
            key='btc',
            name='Bitcoin',
            native_symbol='BTC',
            decimals=8,
            explorer_url='https://blockstream.info',
            explorer_api_url='https://blockstream.info/api',
            is_testnet=False,
            is_active=True,
            required_confirmations=2
        )
        
        # Set up OXA Pay API key
        self.api_key = 'test_api_key_12345'
        settings.OXAPAY_API_KEY = self.api_key
        
        self.client = Client()
    
    def _create_hmac_signature(self, body: str) -> str:
        """Create HMAC-SHA512 signature"""
        return hmac.new(
            self.api_key.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    def test_complete_crypto_payment_flow(self):
        """Test complete flow: create order -> webhook confirms payment -> order paid"""
        from rest_framework.test import APIClient
        
        api_client = APIClient()
        api_client.force_authenticate(user=self.user)
        
        # Step 1: Add item to cart
        cart_url = reverse('cart-add-item')
        api_client.post(cart_url, {
            'account_id': str(self.account.id),
            'quantity': 1
        }, format='json')
        
        # Step 2: Create order with crypto payment method
        order_url = reverse('order-list')
        order_response = api_client.post(order_url, {
            'recipient': {
                'name': 'Test User',
                'email': 'test@example.com'
            },
            'payment_method': 'crypto'
        }, format='json')
        
        self.assertEqual(order_response.status_code, 201)
        order_id = order_response.data['id']
        order_number = order_response.data['order_number']
        
        # Verify order is pending
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'pending')
        
        # Step 3: Simulate OXA Pay invoice creation (would happen in real flow)
        # In real flow, frontend calls generateInvoice API, which creates OxaPayPayment
        
        # Step 4: Send webhook confirming payment
        payload = {
            'track_id': 'test_track_123',
            'status': 'Paid',
            'amount': 95.00,
            'value': 95.00,
            'sent_value': 95.00,
            'currency': 'USD',
            'order_id': order_number,
            'email': self.user.email,
            'type': 'invoice',
            'txs': [{
                'status': 'confirmed',
                'tx_hash': '0x1234567890abcdef',
                'sent_amount': 95.00,
                'received_amount': 95.00,
                'currency': 'USD',
                'network': 'Ethereum',
                'address': '0xabcdef1234567890',
                'confirmations': 12
            }]
        }
        
        body = json.dumps(payload)
        signature = self._create_hmac_signature(body)
        
        webhook_response = self.client.post(
            '/api/v2/wallet/webhook/',
            data=body,
            content_type='application/json',
            HTTP_HMAC=signature
        )
        
        self.assertEqual(webhook_response.status_code, 200)
        
        # Step 5: Verify order is now paid
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Step 6: Verify transaction was created
        transaction = Transaction.objects.filter(
            related_order_id=order.id
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.direction, 'debit')
        self.assertEqual(transaction.category, 'purchase')
        self.assertEqual(transaction.status, 'completed')
        
        # Step 7: Verify cart is cleared
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

