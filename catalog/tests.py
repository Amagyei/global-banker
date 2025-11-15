from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Country, Bank, Account

User = get_user_model()


class CatalogTests(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create countries
        self.us = Country.objects.create(
            code='US',
            name='United States',
            currency_code='USD',
            is_supported=True
        )
        self.uk = Country.objects.create(
            code='UK',
            name='United Kingdom',
            currency_code='GBP',
            is_supported=True
        )
        
        # Create banks
        self.chase = Bank.objects.create(
            name='Chase',
            country=self.us,
            is_active=True
        )
        self.barclays = Bank.objects.create(
            name='Barclays',
            country=self.uk,
            is_active=True
        )
        
        # Create accounts
        self.account1 = Account.objects.create(
            name='Chase Premium',
            description='Premium account',
            bank=self.chase,
            balance_minor=100000,
            price_minor=9500,
            is_active=True
        )
        self.account2 = Account.objects.create(
            name='Barclays Classic',
            description='Classic account',
            bank=self.barclays,
            balance_minor=50000,
            price_minor=4500,
            is_active=True
        )

    def test_list_countries(self):
        """Test listing countries"""
        url = reverse('country-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_banks_by_country(self):
        """Test filtering banks by country"""
        url = reverse('bank-list')
        res = self.client.get(url, {'country': 'US'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], 'Chase')

    def test_list_accounts_by_country(self):
        """Test filtering accounts by country"""
        url = reverse('account-list')
        res = self.client.get(url, {'country': 'US'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], 'Chase Premium')

    def test_account_price_always_usd(self):
        """Test that account prices are always in USD"""
        url = reverse('account-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Check that price starts with $ regardless of account currency
        for account in res.data:
            self.assertTrue(account['price'].startswith('$'))

    def test_exclude_purchased_accounts(self):
        """Test that purchased accounts are excluded for authenticated users"""
        from orders.models import Order, OrderItem
        
        # Create an order with account1
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
        
        # Login
        self.client.force_authenticate(user=self.user)
        
        # Get accounts - account1 should be excluded
        url = reverse('account-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        account_ids = [acc['id'] for acc in res.data]
        self.assertNotIn(str(self.account1.id), account_ids)
        self.assertIn(str(self.account2.id), account_ids)

    def test_account_sku_auto_generated(self):
        """Test that SKU is auto-generated"""
        self.assertIsNotNone(self.account1.sku)
        self.assertTrue(self.account1.sku.startswith('CHASE-'))

    def test_account_currency_property(self):
        """Test that account currency comes from bank's country"""
        self.assertEqual(self.account1.currency_code, 'USD')
        self.assertEqual(self.account2.currency_code, 'GBP')
