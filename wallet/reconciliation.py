"""
Reconciliation Service - Compares database records with blockchain state.
Detects discrepancies between expected and actual balances.
"""
import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from django.db import models
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class ReconciliationService:
    """
    Service for reconciling wallet balances and transactions.
    Compares:
    1. User wallet balances vs transaction history
    2. On-chain transactions vs database records
    3. OXA Pay payments vs credited amounts
    """
    
    def __init__(self):
        self.discrepancies = []
        self.summary = {}
    
    def run_full_reconciliation(self) -> Dict[str, Any]:
        """
        Run full reconciliation check.
        
        Returns:
            Dict with reconciliation report
        """
        self.discrepancies = []
        self.summary = {
            'started_at': timezone.now().isoformat(),
            'users_checked': 0,
            'transactions_checked': 0,
            'payments_checked': 0,
            'discrepancies_found': 0,
        }
        
        try:
            # Run all reconciliation checks
            self._reconcile_wallet_balances()
            self._reconcile_onchain_transactions()
            self._reconcile_oxapay_payments()
            self._check_duplicate_payments()
            
            self.summary['completed_at'] = timezone.now().isoformat()
            self.summary['discrepancies_found'] = len(self.discrepancies)
            self.summary['status'] = 'completed'
            
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}", exc_info=True)
            self.summary['status'] = 'failed'
            self.summary['error'] = str(e)
        
        return {
            'summary': self.summary,
            'discrepancies': self.discrepancies
        }
    
    def _reconcile_wallet_balances(self):
        """
        Verify wallet balances match transaction history.
        For each user, sum all transactions and compare with wallet balance.
        """
        from .models import Wallet
        from transactions.models import Transaction
        
        wallets = Wallet.objects.all().select_related('user')
        
        for wallet in wallets:
            try:
                # Calculate expected balance from transaction history
                transactions = Transaction.objects.filter(
                    user=wallet.user,
                    status='completed'
                )
                
                expected_balance = 0
                for tx in transactions:
                    if tx.direction == 'credit':
                        expected_balance += tx.amount_minor
                    elif tx.direction == 'debit':
                        expected_balance -= tx.amount_minor
                
                # Compare with actual balance
                actual_balance = wallet.balance_minor
                
                if expected_balance != actual_balance:
                    self.discrepancies.append({
                        'type': 'wallet_balance_mismatch',
                        'user_id': str(wallet.user.id),
                        'user_email': wallet.user.email,
                        'expected_balance': expected_balance,
                        'actual_balance': actual_balance,
                        'difference': actual_balance - expected_balance,
                        'severity': 'high' if abs(actual_balance - expected_balance) > 10000 else 'medium',
                    })
                
                self.summary['users_checked'] = self.summary.get('users_checked', 0) + 1
                
            except Exception as e:
                logger.error(f"Error reconciling wallet for user {wallet.user.email}: {e}")
    
    def _reconcile_onchain_transactions(self):
        """
        Verify on-chain transactions are properly credited.
        Check that all confirmed on-chain transactions have corresponding wallet credits.
        """
        from .models import OnChainTransaction
        from transactions.models import Transaction
        
        # Get all confirmed on-chain transactions
        onchain_txs = OnChainTransaction.objects.filter(status='confirmed')
        
        for onchain_tx in onchain_txs:
            try:
                # Check if there's a corresponding transaction record
                related_tx = Transaction.objects.filter(
                    related_onchain_tx_id=onchain_tx.id,
                    status='completed'
                ).first()
                
                if not related_tx:
                    self.discrepancies.append({
                        'type': 'missing_credit',
                        'onchain_tx_id': str(onchain_tx.id),
                        'tx_hash': onchain_tx.tx_hash,
                        'user_email': onchain_tx.user.email,
                        'amount_minor': onchain_tx.amount_minor,
                        'severity': 'high',
                        'description': 'Confirmed on-chain transaction not credited to wallet',
                    })
                elif related_tx.amount_minor != onchain_tx.amount_minor:
                    self.discrepancies.append({
                        'type': 'amount_mismatch',
                        'onchain_tx_id': str(onchain_tx.id),
                        'tx_hash': onchain_tx.tx_hash,
                        'user_email': onchain_tx.user.email,
                        'onchain_amount': onchain_tx.amount_minor,
                        'credited_amount': related_tx.amount_minor,
                        'difference': onchain_tx.amount_minor - related_tx.amount_minor,
                        'severity': 'high',
                    })
                
                self.summary['transactions_checked'] = self.summary.get('transactions_checked', 0) + 1
                
            except Exception as e:
                logger.error(f"Error reconciling on-chain tx {onchain_tx.tx_hash[:20]}...: {e}")
    
    def _reconcile_oxapay_payments(self):
        """
        Verify OXA Pay payments are properly credited.
        Check that all paid OXA Pay payments have corresponding wallet credits.
        """
        from .models import OxaPayPayment
        from transactions.models import Transaction
        
        # Get all paid OXA Pay payments
        paid_payments = OxaPayPayment.objects.filter(status='paid')
        
        for payment in paid_payments:
            try:
                # Check if payment is for a top-up (not an order)
                if payment.topup_intent and not payment.order_id.startswith('ORD-'):
                    # This is a wallet top-up
                    related_tx = Transaction.objects.filter(
                        user=payment.user,
                        category='topup',
                        status='completed',
                        created_at__gte=payment.created_at,
                        amount_minor=int(payment.amount * 100)
                    ).first()
                    
                    if not related_tx:
                        self.discrepancies.append({
                            'type': 'missing_topup_credit',
                            'payment_track_id': payment.track_id,
                            'user_email': payment.user.email,
                            'amount': float(payment.amount),
                            'severity': 'high',
                            'description': 'Paid OXA Pay payment not credited to wallet',
                        })
                
                self.summary['payments_checked'] = self.summary.get('payments_checked', 0) + 1
                
            except Exception as e:
                logger.error(f"Error reconciling OXA Pay payment {payment.track_id}: {e}")
    
    def _check_duplicate_payments(self):
        """
        Check for duplicate payments (same tx_hash or track_id).
        """
        from .models import OxaPayPayment, OnChainTransaction
        from django.db.models import Count
        
        # Check for duplicate OXA Pay payments by track_id
        duplicate_oxapay = OxaPayPayment.objects.values('track_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        for dup in duplicate_oxapay:
            self.discrepancies.append({
                'type': 'duplicate_oxapay_payment',
                'track_id': dup['track_id'],
                'count': dup['count'],
                'severity': 'high',
            })
        
        # Check for duplicate on-chain transactions by tx_hash
        duplicate_onchain = OnChainTransaction.objects.values('tx_hash').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        for dup in duplicate_onchain:
            self.discrepancies.append({
                'type': 'duplicate_onchain_tx',
                'tx_hash': dup['tx_hash'],
                'count': dup['count'],
                'severity': 'high',
            })
    
    def get_user_reconciliation(self, user) -> Dict[str, Any]:
        """
        Get reconciliation report for a specific user.
        
        Args:
            user: User instance
            
        Returns:
            Dict with user-specific reconciliation data
        """
        from .models import Wallet, OnChainTransaction, OxaPayPayment
        from transactions.models import Transaction
        
        report = {
            'user_id': str(user.id),
            'user_email': user.email,
            'checked_at': timezone.now().isoformat(),
        }
        
        try:
            # Get wallet
            wallet = Wallet.objects.filter(user=user).first()
            if wallet:
                report['wallet_balance'] = wallet.balance_minor / 100
            else:
                report['wallet_balance'] = 0
            
            # Calculate expected balance from transactions
            transactions = Transaction.objects.filter(user=user, status='completed')
            expected = 0
            for tx in transactions:
                if tx.direction == 'credit':
                    expected += tx.amount_minor
                else:
                    expected -= tx.amount_minor
            
            report['expected_balance'] = expected / 100
            report['balance_matches'] = (wallet.balance_minor if wallet else 0) == expected
            
            # Get transaction counts
            report['total_credits'] = transactions.filter(direction='credit').count()
            report['total_debits'] = transactions.filter(direction='debit').count()
            
            # Get on-chain transaction counts
            report['onchain_pending'] = OnChainTransaction.objects.filter(
                user=user, status='pending'
            ).count()
            report['onchain_confirmed'] = OnChainTransaction.objects.filter(
                user=user, status='confirmed'
            ).count()
            
            # Get OXA Pay payment counts
            report['oxapay_pending'] = OxaPayPayment.objects.filter(
                user=user, status='pending'
            ).count()
            report['oxapay_paid'] = OxaPayPayment.objects.filter(
                user=user, status='paid'
            ).count()
            
        except Exception as e:
            report['error'] = str(e)
        
        return report


class DuplicatePaymentDetector:
    """
    Detects and prevents duplicate payments.
    """
    
    @staticmethod
    def check_duplicate_oxapay(track_id: str) -> bool:
        """
        Check if an OXA Pay payment with this track_id already exists.
        
        Returns:
            True if duplicate exists, False otherwise
        """
        from .models import OxaPayPayment
        return OxaPayPayment.objects.filter(track_id=track_id).exists()
    
    @staticmethod
    def check_duplicate_onchain(tx_hash: str) -> bool:
        """
        Check if an on-chain transaction with this hash already exists.
        
        Returns:
            True if duplicate exists, False otherwise
        """
        from .models import OnChainTransaction
        return OnChainTransaction.objects.filter(tx_hash=tx_hash).exists()
    
    @staticmethod
    def check_duplicate_webhook(track_id: str, status: str) -> bool:
        """
        Check if this webhook has already been processed.
        Uses a cache key to prevent duplicate processing.
        
        Returns:
            True if already processed, False otherwise
        """
        from django.core.cache import cache
        
        cache_key = f"webhook_processed:{track_id}:{status}"
        
        if cache.get(cache_key):
            logger.warning(f"Duplicate webhook detected: {track_id} with status {status}")
            return True
        
        # Mark as processed (cache for 1 hour)
        cache.set(cache_key, True, 3600)
        return False
    
    @staticmethod
    def prevent_double_credit(user_id: str, amount_minor: int, source_type: str, source_id: str) -> bool:
        """
        Prevent double crediting by checking if this credit already exists.
        
        Args:
            user_id: User ID
            amount_minor: Amount in minor units
            source_type: Type of source (onchain_tx, oxapay, etc.)
            source_id: Source ID
            
        Returns:
            True if credit already exists, False otherwise
        """
        from transactions.models import Transaction
        from django.core.cache import cache
        
        # Check cache first
        cache_key = f"credit:{user_id}:{source_type}:{source_id}"
        if cache.get(cache_key):
            logger.warning(f"Duplicate credit prevented: {cache_key}")
            return True
        
        # Check database
        if source_type == 'onchain_tx':
            exists = Transaction.objects.filter(
                related_onchain_tx_id=source_id,
                status='completed'
            ).exists()
        else:
            # Generic check
            exists = Transaction.objects.filter(
                user_id=user_id,
                amount_minor=amount_minor,
                description__contains=source_id,
                status='completed'
            ).exists()
        
        if exists:
            # Cache the result
            cache.set(cache_key, True, 3600)
            return True
        
        return False

