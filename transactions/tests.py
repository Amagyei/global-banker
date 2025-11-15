from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Transaction

User = get_user_model()


class TransactionTests(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create transactions
        self.transaction1 = Transaction.objects.create(
            user=self.user,
            direction='debit',
            category='purchase',
            amount_minor=9500,
            currency_code='USD',
            description='Test purchase',
            balance_after_minor=50000,
            status='completed'
        )
        self.transaction2 = Transaction.objects.create(
            user=self.user,
            direction='credit',
            category='topup',
            amount_minor=100000,
            currency_code='USD',
            description='Wallet top up',
            balance_after_minor=150000,
            status='pending'
        )

    def test_list_transactions_requires_auth(self):
        """Test that listing transactions requires authentication"""
        url = reverse('transaction-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_transactions(self):
        """Test listing user's transactions"""
        self.client.force_authenticate(user=self.user)
        url = reverse('transaction-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_transactions_by_direction(self):
        """Test filtering transactions by direction"""
        self.client.force_authenticate(user=self.user)
        url = reverse('transaction-list')
        res = self.client.get(url, {'direction': 'debit'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['direction'], 'debit')

    def test_filter_transactions_by_category(self):
        """Test filtering transactions by category"""
        self.client.force_authenticate(user=self.user)
        url = reverse('transaction-list')
        res = self.client.get(url, {'category': 'topup'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['category'], 'topup')

    def test_filter_transactions_by_status(self):
        """Test filtering transactions by status"""
        self.client.force_authenticate(user=self.user)
        url = reverse('transaction-list')
        res = self.client.get(url, {'status': 'pending'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['status'], 'pending')

    def test_transaction_amount_formatting(self):
        """Test that transaction amounts are formatted correctly"""
        self.client.force_authenticate(user=self.user)
        url = reverse('transaction-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Check debit has negative sign
        debit_tx = next(tx for tx in res.data if tx['direction'] == 'debit')
        self.assertTrue(debit_tx['amount'].startswith('-'))
        # Check credit has positive sign
        credit_tx = next(tx for tx in res.data if tx['direction'] == 'credit')
        self.assertTrue(credit_tx['amount'].startswith('+'))

    def test_transactions_user_isolation(self):
        """Test that users only see their own transactions"""
        other_user = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123'
        )
        Transaction.objects.create(
            user=other_user,
            direction='debit',
            category='purchase',
            amount_minor=5000,
            currency_code='USD',
            description='Other user purchase',
            balance_after_minor=10000,
            status='completed'
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('transaction-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)  # Only this user's transactions
