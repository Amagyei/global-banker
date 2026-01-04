from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Cart, CartItem, Order, OrderItem, Fulfillment
from catalog.models import Country, Bank, Account
from wallet.models import Wallet

User = get_user_model()


class CartTests(APITestCase):
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
        # MoneyField stores dollars, not cents
        self.account1 = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=1000,  # $1000.00
            price_minor=95,      # $95.00
            is_active=True
        )
        self.account2 = Account.objects.create(
            name='Chase Classic',
            description='Classic account',
            bank=self.chase,
            balance_minor=500,   # $500.00
            price_minor=45,      # $45.00
            is_active=True
        )

    def test_get_cart_requires_auth(self):
        """Test that getting cart requires authentication"""
        url = reverse('cart-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_cart_creates_if_not_exists(self):
        """Test that cart is created automatically"""
        self.client.force_authenticate(user=self.user)
        url = reverse('cart-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_add_item_to_cart(self):
        """Test adding item to cart"""
        self.client.force_authenticate(user=self.user)
        url = reverse('cart-add-item')
        data = {
            'account_id': str(self.account1.id),
            'quantity': 1
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CartItem.objects.filter(cart__user=self.user, account=self.account1).exists())

    def test_add_item_increases_quantity(self):
        """Test that adding same item increases quantity"""
        self.client.force_authenticate(user=self.user)
        url = reverse('cart-add-item')
        data = {'account_id': str(self.account1.id), 'quantity': 1}
        
        # Add first time
        res1 = self.client.post(url, data, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        # Add second time
        res2 = self.client.post(url, data, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        
        cart_item = CartItem.objects.get(cart__user=self.user, account=self.account1)
        self.assertEqual(cart_item.quantity, 2)

    def test_cart_price_always_usd(self):
        """Test that cart prices are always in USD"""
        self.client.force_authenticate(user=self.user)
        url = reverse('cart-add-item')
        data = {'account_id': str(self.account1.id), 'quantity': 1}
        self.client.post(url, data, format='json')
        
        # Get cart
        cart_url = reverse('cart-list')
        res = self.client.get(cart_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data[0]['total'].startswith('$'))
        self.assertTrue(res.data[0]['items'][0]['unit_price'].startswith('$'))

    def test_cannot_add_purchased_account(self):
        """Test that user cannot add already purchased account"""
        # Create order with account1
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=9500,
            fees_minor=0,
            total_minor=9500,
            currency_code='USD',
            recipient={'name': 'Test'},
            status='paid'
        )
        OrderItem.objects.create(
            order=order,
            account=self.account1,
            quantity=1,
            unit_price_minor=9500
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('cart-add-item')
        data = {'account_id': str(self.account1.id), 'quantity': 1}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already purchased', res.data['detail'].lower())

    def test_update_cart_item_quantity(self):
        """Test updating cart item quantity"""
        self.client.force_authenticate(user=self.user)
        # Add item first
        add_url = reverse('cart-add-item')
        self.client.post(add_url, {'account_id': str(self.account1.id), 'quantity': 1}, format='json')
        
        cart_item = CartItem.objects.get(cart__user=self.user, account=self.account1)
        update_url = reverse('cartitem-detail', kwargs={'pk': cart_item.id})
        res = self.client.patch(update_url, {'quantity': 3}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['quantity'], 3)

    def test_remove_cart_item(self):
        """Test removing item from cart"""
        self.client.force_authenticate(user=self.user)
        # Add item first
        add_url = reverse('cart-add-item')
        self.client.post(add_url, {'account_id': str(self.account1.id), 'quantity': 1}, format='json')
        
        cart_item = CartItem.objects.get(cart__user=self.user, account=self.account1)
        delete_url = reverse('cartitem-detail', kwargs={'pk': cart_item.id})
        res = self.client.delete(delete_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())


class OrderTests(APITestCase):
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
        # MoneyField stores dollars, not cents
        self.account1 = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=1000,  # $1000.00
            price_minor=95,      # $95.00
            is_active=True
        )
        
        # Create cart with item - MoneyField stores dollars
        self.cart = Cart.objects.create(user=self.user, currency_code='USD')
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            account=self.account1,
            quantity=1,
            unit_price_minor=95  # $95.00
        )
        
        # Create wallet with sufficient balance for purchases
        self.wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            balance_minor=1000  # $1000.00
        )

    def test_create_order_requires_auth(self):
        """Test that creating order requires authentication"""
        url = reverse('order-list')
        res = self.client.post(url, {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_from_cart(self):
        """Test creating order from cart"""
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        data = {
            'recipient': {
                'name': 'Test User',
                'email': 'test@example.com'
            }
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('order_number', res.data)
        self.assertEqual(res.data['status'], 'paid')  # Wallet payment marks order as paid
        self.assertEqual(res.data['total'], '$95.00')

    def test_create_order_creates_transaction(self):
        """Test that creating order creates a transaction"""
        from transactions.models import Transaction
        
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        data = {
            'recipient': {
                'name': 'Test User',
                'email': 'test@example.com'
            }
        }
        res = self.client.post(url, data, format='json')
        order_id = res.data['id']
        
        # Check transaction was created
        transaction = Transaction.objects.filter(related_order_id=order_id).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.direction, 'debit')
        self.assertEqual(transaction.category, 'purchase')
        self.assertEqual(transaction.status, 'completed')  # Wallet payment completes transaction

    def test_create_order_clears_cart(self):
        """Test that creating order clears cart"""
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        data = {
            'recipient': {
                'name': 'Test User',
                'email': 'test@example.com'
            }
        }
        self.client.post(url, data, format='json')
        
        # Check cart is empty
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

    def test_create_order_empty_cart_fails(self):
        """Test that creating order with empty cart fails"""
        # Clear cart
        self.cart.items.all().delete()
        
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        data = {
            'recipient': {
                'name': 'Test User',
                'email': 'test@example.com'
            }
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('empty', res.data['detail'].lower())

    def test_list_orders(self):
        """Test listing user's orders"""
        # Create an order - MoneyField stores dollars
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=95,  # $95.00
            fees_minor=0,
            total_minor=95,     # $95.00
            currency_code='USD',
            recipient={'name': 'Test'},
            status='paid'
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['order_number'], order.order_number)

    def test_order_price_always_usd(self):
        """Test that order prices are always in USD"""
        # MoneyField stores dollars
        order = Order.objects.create(
            user=self.user,
            subtotal_minor=95,  # $95.00
            fees_minor=0,
            total_minor=95,     # $95.00
            currency_code='USD',
            recipient={'name': 'Test'},
            status='paid'
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('order-detail', kwargs={'pk': order.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['total'].startswith('$'))
        self.assertTrue(res.data['subtotal'].startswith('$'))

    def test_orders_user_isolation(self):
        """Test that users only see their own orders"""
        other_user = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123'
        )
        # MoneyField stores dollars
        Order.objects.create(
            user=other_user,
            subtotal_minor=50,  # $50.00
            fees_minor=0,
            total_minor=50,     # $50.00
            currency_code='USD',
            recipient={'name': 'Other'},
            status='paid'
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)  # No orders for this user


class IntegrationTests(APITestCase):
    """Integration tests for complete workflows"""
    
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
        # MoneyField stores dollars
        self.account = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=1000,  # $1000.00
            price_minor=95,      # $95.00
            is_active=True
        )
        
        # Create wallet with sufficient balance for purchases
        self.wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            balance_minor=1000  # $1000.00
        )

    def test_complete_purchase_workflow(self):
        """Test complete purchase workflow: browse -> add to cart -> checkout -> order -> transaction"""
        self.client.force_authenticate(user=self.user)
        
        # 1. Browse accounts
        account_url = reverse('account-list')
        res = self.client.get(account_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreater(len(res.data), 0)
        
        # 2. Add to cart
        cart_add_url = reverse('cart-add-item')
        res = self.client.post(cart_add_url, {
            'account_id': str(self.account.id),
            'quantity': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # 3. Create order
        order_url = reverse('order-list')
        res = self.client.post(order_url, {
            'recipient': {
                'name': 'Test User',
                'email': 'test@example.com'
            }
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id = res.data['id']
        
        # 4. Verify transaction created
        from transactions.models import Transaction
        transaction = Transaction.objects.filter(related_order_id=order_id).first()
        self.assertIsNotNone(transaction)
        
        # 5. Mark order as paid so account is excluded
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        order.status = 'paid'
        order.save()
        
        # 6. Verify account is now excluded from catalog
        res = self.client.get(account_url)
        account_ids = [acc['id'] for acc in res.data]
        self.assertNotIn(str(self.account.id), account_ids)

    def test_purchase_then_cannot_rebuy(self):
        """Test that after purchase, user cannot add same item to cart again"""
        self.client.force_authenticate(user=self.user)
        
        # Purchase account
        cart_add_url = reverse('cart-add-item')
        self.client.post(cart_add_url, {
            'account_id': str(self.account.id),
            'quantity': 1
        }, format='json')
        
        order_url = reverse('order-list')
        order_res = self.client.post(order_url, {
            'recipient': {'name': 'Test', 'email': 'test@example.com'}
        }, format='json')
        order_id = order_res.data['id']
        
        # Mark order as paid
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        order.status = 'paid'
        order.save()
        
        # Try to add same account again - should fail
        res = self.client.post(cart_add_url, {
            'account_id': str(self.account.id),
            'quantity': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
