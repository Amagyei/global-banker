"""
Comprehensive tests for email notification functionality
"""
import logging
from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from orders.models import Order, OrderItem, Cart, CartItem
from catalog.models import Country, Bank, Account, FullzPackage
from wallet.models import Wallet, OxaPayPayment, CryptoNetwork
from notifications.services import send_order_confirmation_email, send_payment_confirmation_email
from notifications.models import EmailNotification

User = get_user_model()


class EmailServiceTests(TestCase):
    """Test email service utilities"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_success(self):
        """Test successful email sending"""
        from notifications.utils import EmailService
        
        result = EmailService.send_email(
            subject='Test Subject',
            message='Test Message',
            recipient_email='test@example.com'
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')
        self.assertEqual(mail.outbox[0].body, 'Test Message')
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
    
    @override_settings(EMAIL_BACKEND=None)
    def test_send_email_no_backend(self):
        """Test email sending when backend not configured"""
        from notifications.utils import EmailService
        
        result = EmailService.send_email(
            subject='Test Subject',
            message='Test Message',
            recipient_email='test@example.com'
        )
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_render_template(self):
        """Test template rendering"""
        from notifications.utils import EmailService
        
        context = {
            'order_number': 'ORD-2024-0001',
            'order_date': '2024-01-01 12:00',
            'items_list': '1x Test Item - $10.00',
            'total': 10.00,
        }
        
        result = EmailService.render_template('emails/order_confirmation.txt', context)
        
        self.assertIn('ORD-2024-0001', result)
        self.assertIn('1x Test Item', result)
        self.assertIn('$10.00', result)


class OrderConfirmationEmailTests(TestCase):
    """Test order confirmation email functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        self.us = Country.objects.create(code='US', name='United States', currency_code='USD', is_supported=True)
        self.chase = Bank.objects.create(name='Chase', country=self.us, is_active=True)
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
        self.wallet = Wallet.objects.create(user=self.user, currency_code='USD', balance_minor=0)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_order_confirmation_email_success(self):
        """Test successful order confirmation email"""
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='paid'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        
        result = send_order_confirmation_email(order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.order_number, mail.outbox[0].subject)
        self.assertIn(order.order_number, mail.outbox[0].body)
        self.assertIn('Chase Premium', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        
        # Verify email notification was logged
        notification = EmailNotification.objects.filter(order=order, email_type='order_confirmation').first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.status, 'sent')
        self.assertEqual(notification.recipient_email, 'test@example.com')
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_order_confirmation_email_with_fullz_package(self):
        """Test order confirmation email with FullzPackage"""
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=2500,
            fees_minor=0,
            total_minor=2500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='paid'
        )
        OrderItem.objects.create(
            order=order,
            fullz_package=self.fullz_package,
            quantity=1,
            unit_price_minor=2500
        )
        
        result = send_order_confirmation_email(order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Starter Pack', mail.outbox[0].body)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_order_confirmation_email_multiple_items(self):
        """Test order confirmation email with multiple items"""
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=12000,
            fees_minor=0,
            total_minor=12000,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='paid'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=9500
        )
        OrderItem.objects.create(
            order=order,
            fullz_package=self.fullz_package,
            quantity=1,
            unit_price_minor=2500
        )
        
        result = send_order_confirmation_email(order)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('Chase Premium', body)
        self.assertIn('Starter Pack', body)
        self.assertIn('$120.00', body)  # Total
    
    def test_send_order_confirmation_email_not_paid(self):
        """Test that email is not sent for non-paid orders"""
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'  # Not paid
        )
        
        result = send_order_confirmation_email(order)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_send_order_confirmation_email_no_user_email(self):
        """Test that email is not sent if user has no email"""
        user_no_email = User.objects.create_user(
            username='noemail@example.com',
            email='',  # No email
            password='testpass123'
        )
        order = Order.objects.create(
            user=user_no_email,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': ''},
            status='paid'
        )
        
        result = send_order_confirmation_email(order)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    @override_settings(EMAIL_BACKEND=None)
    def test_send_order_confirmation_email_no_backend(self):
        """Test order confirmation email when backend not configured"""
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='paid'
        )
        
        result = send_order_confirmation_email(order)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
        # But notification should still be logged as failed
        notification = EmailNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.status, 'failed')


class PaymentConfirmationEmailTests(TestCase):
    """Test payment confirmation email functionality"""
    
    def setUp(self):
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
            track_id='test_track_123',
            amount=100.00,
            currency='USD',
            pay_currency='btc',
            address='bc1qtest',
            status='pending'
        )
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_payment_confirmation_email_success(self):
        """Test successful payment confirmation email"""
        result = send_payment_confirmation_email(
            user=self.user,
            payment=self.payment,
            status='success',
            amount=100.00
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Confirmed', mail.outbox[0].subject)
        self.assertIn('$100.00', mail.outbox[0].body)
        self.assertIn(self.payment.track_id, mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        
        # Verify email notification was logged
        notification = EmailNotification.objects.filter(
            user=self.user,
            email_type='payment_confirmation',
            status='sent'
        ).first()
        self.assertIsNotNone(notification)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_payment_confirmation_email_failed(self):
        """Test failed payment confirmation email"""
        result = send_payment_confirmation_email(
            user=self.user,
            payment=self.payment,
            status='failed',
            amount=100.00
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Failed', mail.outbox[0].subject)
        self.assertIn('$100.00', mail.outbox[0].body)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_payment_confirmation_email_expired(self):
        """Test expired payment confirmation email"""
        result = send_payment_confirmation_email(
            user=self.user,
            payment=self.payment,
            status='expired',
            amount=100.00
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Expired', mail.outbox[0].subject)
        self.assertIn('$100.00', mail.outbox[0].body)
    
    def test_send_payment_confirmation_email_no_user_email(self):
        """Test that email is not sent if user has no email"""
        user_no_email = User.objects.create_user(
            username='noemail@example.com',
            email='',
            password='testpass123'
        )
        
        result = send_payment_confirmation_email(
            user=user_no_email,
            payment=self.payment,
            status='success',
            amount=100.00
        )
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)


class EmailNotificationModelTests(TestCase):
    """Test EmailNotification model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_email_notification_creation(self):
        """Test creating email notification record"""
        notification = EmailNotification.objects.create(
            user=self.user,
            email_type='order_confirmation',
            status='sent',
            recipient_email='test@example.com'
        )
        
        self.assertIsNotNone(notification.id)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.email_type, 'order_confirmation')
        self.assertEqual(notification.status, 'sent')
        self.assertIsNotNone(notification.sent_at)
    
    def test_email_notification_with_order(self):
        """Test email notification with order"""
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='paid'
        )
        
        notification = EmailNotification.objects.create(
            user=self.user,
            order=order,
            email_type='order_confirmation',
            status='sent',
            recipient_email='test@example.com'
        )
        
        self.assertEqual(notification.order, order)
        self.assertEqual(notification.email_type, 'order_confirmation')


class IntegrationTests(TestCase):
    """Integration tests for email sending in order flow"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        self.us = Country.objects.create(code='US', name='United States', currency_code='USD', is_supported=True)
        self.chase = Bank.objects.create(name='Chase', country=self.us, is_active=True)
        self.account = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=100000,
            price_minor=9500,
            is_active=True
        )
        self.wallet = Wallet.objects.create(user=self.user, currency_code='USD', balance_minor=100000)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_wallet_payment_sends_email(self):
        """Test that wallet payment triggers order confirmation email"""
        from orders.models import Cart, CartItem
        from transactions.models import Transaction
        
        # Create cart with item - all fields are now MoneyField (dollars)
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            account=self.account,
            quantity=1,
            unit_price_minor=self.account.price_minor.amount
        )
        
        # Update wallet balance to have enough funds (MoneyField stores dollars)
        self.wallet.balance_minor = 1000  # $1000.00
        self.wallet.save()
        
        # All fields are now MoneyField (dollars)
        price = self.account.price_minor.amount
        
        # Create order and simulate wallet payment flow
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=price,
            fees_minor=0,
            total_minor=price,
            currency_code='USD',
            recipient={'name': 'Test User', 'email': 'test@example.com'},
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account,
            quantity=1,
            unit_price_minor=price
        )
        
        # Simulate wallet payment: deduct balance, create transaction, mark as paid
        self.wallet.balance_minor -= order.total_minor.amount
        self.wallet.save()
        
        Transaction.objects.create(
            user=self.user,
            direction='debit',
            category='purchase',
            amount_minor=order.total_minor.amount,
            currency_code='USD',
            description=f'Order {order.order_number}',
            balance_after_minor=self.wallet.balance_minor.amount,
            status='completed',
            related_order_id=order.id,
        )
        
        # Mark order as paid (this triggers email in views.py)
        order.status = 'paid'
        order.save()
        
        # Manually trigger email (simulating what happens in views.py)
        send_order_confirmation_email(order)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Order Confirmation', mail.outbox[0].subject)
        self.assertIn(order.order_number, mail.outbox[0].body)
        
        # Verify notification was logged
        notification = EmailNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.email_type, 'order_confirmation')
        self.assertEqual(notification.status, 'sent')
