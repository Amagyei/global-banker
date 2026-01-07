"""
Celery tasks for wallet operations:
- Deposit monitoring
- Sweep operations
- Reconciliation
- Transaction alerts
"""
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal

logger = logging.getLogger(__name__)


# ============================================================================
# DEPOSIT MONITORING TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_deposits_task(self):
    """
    Monitor all active deposit addresses for incoming transactions.
    Runs every 2 minutes via Celery Beat.
    Detects deposits, creates OnChainTransaction records, and processes confirmed transactions.
    """
    from .models import DepositAddress, TopUpIntent, CryptoNetwork, OnChainTransaction
    from .blockchain import BlockchainMonitor
    
    try:
        # Get all active networks
        networks = CryptoNetwork.objects.filter(is_active=True)
        
        deposits_found = 0
        confirmed_count = 0
        
        for network in networks:
            try:
                monitor = BlockchainMonitor(network)
                
                # Get pending top-up intents for this network
                pending_intents = TopUpIntent.objects.filter(
                    network=network,
                    status='pending',
                    deposit_address__isnull=False
                ).select_related('deposit_address', 'user')
                
                for intent in pending_intents:
                    if intent.deposit_address:
                        found = monitor.check_deposit_address(
                            intent.deposit_address,
                            intent
                        )
                        if found:
                            deposits_found += 1
                            logger.info(f"Found deposit for intent {intent.id}")
                
                # Also check for any confirmed transactions that need processing
                # (in case deposits came in without a topup_intent or were missed)
                # _process_confirmed_transaction is idempotent (checks for duplicates)
                confirmed_txs = OnChainTransaction.objects.filter(
                    network=network,
                    status='confirmed'
                ).select_related('user', 'topup_intent')
                
                for tx in confirmed_txs:
                    # Process confirmed transaction (triggers sweep if needed)
                    # This is safe to call multiple times - it checks for duplicates
                    try:
                        monitor._process_confirmed_transaction(tx)
                        confirmed_count += 1
                        logger.info(f"Processed confirmed transaction {tx.tx_hash[:20]}...")
                    except Exception as e:
                        logger.error(f"Error processing confirmed transaction {tx.id}: {e}")
                            
            except Exception as e:
                logger.error(f"Error monitoring network {network.key}: {e}")
                continue
        
        logger.info(f"Deposit monitoring complete. Found {deposits_found} new deposits, processed {confirmed_count} confirmed transactions.")
        return {'deposits_found': deposits_found, 'confirmed_processed': confirmed_count}
        
    except Exception as e:
        logger.error(f"Deposit monitoring task failed: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def sweep_deposits_task(self):
    """
    Sweep confirmed deposits from user addresses to hot wallet.
    Runs every 5 minutes via Celery Beat.
    """
    from .models import OnChainTransaction, SweepTransaction
    from .sweep_service import SweepService
    from .blockchain import BlockchainMonitor
    
    try:
        sweep_service = SweepService()
        
        # Find confirmed transactions that haven't been swept
        confirmed_txs = OnChainTransaction.objects.filter(
            status='confirmed'
        ).exclude(
            id__in=SweepTransaction.objects.values_list('onchain_tx_id', flat=True)
        )
        
        sweeps_created = 0
        for tx in confirmed_txs:
            try:
                sweep_tx = sweep_service.sweep_deposit(tx)
                sweeps_created += 1
                logger.info(f"Created sweep {sweep_tx.id} for transaction {tx.tx_hash[:20]}...")
            except Exception as e:
                logger.error(f"Failed to sweep transaction {tx.tx_hash[:20]}...: {e}")
                # Send alert for failed sweep
                send_transaction_alert.delay(
                    alert_type='sweep_failed',
                    tx_hash=tx.tx_hash,
                    amount=tx.amount_minor / 100,
                    error=str(e)
                )
        
        # Check for confirmed sweeps and credit wallets
        confirmed_sweeps = SweepTransaction.objects.filter(
            status='broadcast',
            onchain_tx__status='confirmed'
        ).select_related('onchain_tx', 'onchain_tx__user', 'network')
        
        wallets_credited = 0
        for sweep in confirmed_sweeps:
            try:
                # Check sweep confirmation status
                monitor = BlockchainMonitor(sweep.network)
                tx_data = monitor.get_transaction(sweep.tx_hash)
                
                if tx_data:
                    # Update sweep confirmations
                    confirmations = monitor.compute_confirmations(
                        tx_data.get('block_height') if tx_data.get('status', {}).get('confirmed') else None
                    )
                    sweep.confirmations = confirmations
                    
                    # If sweep is confirmed, credit wallet
                    if confirmations >= sweep.required_confirmations and sweep.status != 'confirmed':
                        sweep.status = 'confirmed'
                        sweep.save()
                        
                        # Credit wallet (this checks for duplicates)
                        from .blockchain import BlockchainMonitor
                        monitor_instance = BlockchainMonitor(sweep.network)
                        monitor_instance._credit_wallet_after_sweep(sweep.onchain_tx, sweep)
                        wallets_credited += 1
                        
                        # Send alert for large deposits
                        if sweep.onchain_tx.amount_minor >= getattr(settings, 'TRANSACTION_ALERT_THRESHOLD_USD', 100) * 100:
                            send_large_deposit_alert.delay(
                                user_email=sweep.onchain_tx.user.email,
                                amount=sweep.onchain_tx.amount_minor / 100,
                                network=sweep.network.name,
                                tx_hash=sweep.tx_hash
                            )
                    else:
                        sweep.save()
            except Exception as e:
                logger.error(f"Error checking sweep {sweep.id} confirmation: {e}")
        
        logger.info(f"Sweep task complete. Created {sweeps_created} sweeps, credited {wallets_credited} wallets.")
        return {'sweeps_created': sweeps_created, 'wallets_credited': wallets_credited}
        
    except Exception as e:
        logger.error(f"Sweep deposits task failed: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def retry_failed_sweeps_task(self):
    """
    Retry failed sweep transactions.
    Runs every 15 minutes via Celery Beat.
    """
    from .models import SweepTransaction
    from .sweep_service import SweepService
    
    try:
        sweep_service = SweepService()
        
        # Find failed sweeps that can be retried
        from django.db.models import F
        failed_sweeps = SweepTransaction.objects.filter(
            status='failed',
            retry_count__lt=F('max_retries')
        )
        
        retries_attempted = 0
        retries_succeeded = 0
        
        for sweep in failed_sweeps:
            try:
                sweep_service.retry_failed_sweep(sweep)
                retries_succeeded += 1
                logger.info(f"Successfully retried sweep {sweep.id}")
            except Exception as e:
                logger.error(f"Retry failed for sweep {sweep.id}: {e}")
            retries_attempted += 1
        
        logger.info(f"Retry task complete. {retries_succeeded}/{retries_attempted} succeeded.")
        return {'attempted': retries_attempted, 'succeeded': retries_succeeded}
        
    except Exception as e:
        logger.error(f"Retry failed sweeps task failed: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=1)
def consolidate_hot_wallet_task(self):
    """
    Consolidate hot wallet funds to cold storage.
    Runs daily at 2 AM via Celery Beat.
    """
    from .models import HotWallet, ColdWallet, ConsolidationTransaction
    from .hot_wallet_manager import HotWalletManager
    
    try:
        manager = HotWalletManager()
        
        # Get all active hot wallets
        hot_wallets = HotWallet.objects.filter(is_active=True)
        
        consolidations = 0
        for hot_wallet in hot_wallets:
            try:
                # Check if balance exceeds threshold (e.g., $1000)
                threshold = int(settings.get('HOT_WALLET_THRESHOLD_USD', 1000)) * 100
                if hot_wallet.balance_atomic > threshold:
                    # Find cold wallet for this network
                    cold_wallet = ColdWallet.objects.filter(
                        network=hot_wallet.network,
                        is_active=True
                    ).first()
                    
                    if cold_wallet:
                        manager.consolidate_to_cold(hot_wallet, cold_wallet)
                        consolidations += 1
                        logger.info(f"Consolidated hot wallet {hot_wallet.id} to cold storage")
                        
                        # Send alert
                        send_transaction_alert.delay(
                            alert_type='consolidation',
                            network=hot_wallet.network.name,
                            amount=hot_wallet.balance_atomic
                        )
            except Exception as e:
                logger.error(f"Failed to consolidate hot wallet {hot_wallet.id}: {e}")
        
        return {'consolidations': consolidations}
        
    except Exception as e:
        logger.error(f"Consolidation task failed: {e}", exc_info=True)
        raise


# ============================================================================
# PAYMENT TASKS
# ============================================================================

@shared_task(bind=True)
def check_expired_payments_task(self):
    """
    Check for expired OXA Pay payments and update their status.
    Runs every 10 minutes via Celery Beat.
    """
    from .models import OxaPayPayment, TopUpIntent
    
    try:
        now = timezone.now()
        
        # Find pending payments that have expired
        expired_payments = OxaPayPayment.objects.filter(
            status='pending',
            expired_at__lt=now
        )
        
        expired_count = 0
        for payment in expired_payments:
            with db_transaction.atomic():
                payment.status = 'expired'
                payment.save()
                
                # Update associated top-up intent
                if payment.topup_intent:
                    payment.topup_intent.status = 'failed'
                    payment.topup_intent.save()
                
                expired_count += 1
                logger.info(f"Marked payment {payment.track_id} as expired")
        
        logger.info(f"Expired payments check complete. Marked {expired_count} as expired.")
        return {'expired_count': expired_count}
        
    except Exception as e:
        logger.error(f"Check expired payments task failed: {e}", exc_info=True)
        raise


# ============================================================================
# RECONCILIATION TASKS
# ============================================================================

@shared_task(bind=True)
def reconciliation_check_task(self):
    """
    Perform reconciliation check between database and blockchain.
    Runs every hour via Celery Beat.
    """
    from .models import Wallet, OnChainTransaction, OxaPayPayment
    from .reconciliation import ReconciliationService
    from transactions.models import Transaction
    
    try:
        service = ReconciliationService()
        report = service.run_full_reconciliation()
        
        # Check for discrepancies
        if report.get('discrepancies'):
            # Send alert for discrepancies
            send_transaction_alert.delay(
                alert_type='reconciliation_discrepancy',
                discrepancies=report['discrepancies'],
                summary=report['summary']
            )
            logger.warning(f"Reconciliation found discrepancies: {report['discrepancies']}")
        else:
            logger.info(f"Reconciliation complete. No discrepancies found.")
        
        return report
        
    except Exception as e:
        logger.error(f"Reconciliation task failed: {e}", exc_info=True)
        send_transaction_alert.delay(
            alert_type='reconciliation_error',
            error=str(e)
        )
        raise


# ============================================================================
# ALERT TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_transaction_alert(self, alert_type: str, **kwargs):
    """
    Send transaction alert email to admin.
    
    Args:
        alert_type: Type of alert (deposit, sweep_failed, reconciliation_discrepancy, etc.)
        **kwargs: Additional context for the alert
    """
    from notifications.utils import EmailService
    
    try:
        alert_email = getattr(settings, 'TRANSACTION_ALERT_EMAIL', 'nakwa234455@gmail.com')
        
        # Build subject and message based on alert type
        subject_map = {
            'large_deposit': '🔔 Large Deposit Detected',
            'deposit_confirmed': '✅ Deposit Confirmed',
            'sweep_failed': '❌ Sweep Failed - Action Required',
            'consolidation': '📦 Hot Wallet Consolidation Complete',
            'reconciliation_discrepancy': '⚠️ Reconciliation Discrepancy Detected',
            'reconciliation_error': '❌ Reconciliation Error',
            'duplicate_payment': '⚠️ Duplicate Payment Detected',
            'payment_failed': '❌ Payment Failed',
            'payment_expired': '⏰ Payment Expired',
        }
        
        subject = f"[Bank Pro] {subject_map.get(alert_type, f'Alert: {alert_type}')}"
        
        # Build message
        message_lines = [
            f"Alert Type: {alert_type}",
            f"Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "Details:",
        ]
        
        for key, value in kwargs.items():
            message_lines.append(f"  - {key}: {value}")
        
        message_lines.extend([
            "",
            "---",
            "This is an automated alert from Bank Pro.",
            "Please review and take action if necessary.",
        ])
        
        message = "\n".join(message_lines)
        
        success = EmailService.send_email(subject, message, alert_email)
        
        if success:
            logger.info(f"Sent {alert_type} alert to {alert_email}")
        else:
            logger.error(f"Failed to send {alert_type} alert")
            raise Exception("Email sending failed")
        
        return {'success': success, 'alert_type': alert_type}
        
    except Exception as e:
        logger.error(f"Failed to send transaction alert: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task
def send_large_deposit_alert(user_email: str, amount: float, network: str, tx_hash: str):
    """Send alert for large deposits (above threshold)"""
    threshold = getattr(settings, 'TRANSACTION_ALERT_THRESHOLD_USD', 100)
    
    if amount >= threshold:
        send_transaction_alert.delay(
            alert_type='large_deposit',
            user_email=user_email,
            amount=f"${amount:.2f}",
            network=network,
            tx_hash=tx_hash
        )

