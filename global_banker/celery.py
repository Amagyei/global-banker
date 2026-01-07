"""
Celery configuration for Global Banker
Handles background tasks: deposit monitoring, sweeps, alerts, reconciliation
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')

# Create Celery app
app = Celery('global_banker')

# Load config from Django settings, using CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Configure periodic tasks (Celery Beat)
# NOTE: Only tasks needed for OXA Pay are enabled
# Deposit monitoring, sweeps, and consolidation are for non-custodial wallets (not used with OXA Pay)
app.conf.beat_schedule = {
    # Run reconciliation check every hour
    # Checks wallet balances vs transaction history, detects duplicates, finds discrepancies
    'reconciliation-check': {
        'task': 'wallet.tasks.reconciliation_check_task',
        'schedule': crontab(minute=0),  # Every hour at :00
        'options': {'queue': 'reconciliation'}
    },
    # Check for expired OXA Pay payments every 10 minutes
    # Marks expired payments and updates top-up intent status
    'check-expired-payments': {
        'task': 'wallet.tasks.check_expired_payments_task',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
        'options': {'queue': 'payments'}
    },
    # Uncomment below if you ever use non-custodial wallet system (xpub derivation):
    # 'monitor-deposits': {
    #     'task': 'wallet.tasks.monitor_deposits_task',
    #     'schedule': crontab(minute='*/2'),
    #     'options': {'queue': 'deposits'}
    # },
    # 'sweep-deposits': {
    #     'task': 'wallet.tasks.sweep_deposits_task',
    #     'schedule': crontab(minute='*/5'),
    #     'options': {'queue': 'sweeps'}
    # },
    # 'consolidate-hot-wallet': {
    #     'task': 'wallet.tasks.consolidate_hot_wallet_task',
    #     'schedule': crontab(hour=2, minute=0),
    #     'options': {'queue': 'consolidation'}
    # },
}

# Task routing (only queues needed for OXA Pay)
app.conf.task_routes = {
    'wallet.tasks.reconciliation_check_task': {'queue': 'reconciliation'},
    'wallet.tasks.check_expired_payments_task': {'queue': 'payments'},
    'wallet.tasks.send_transaction_alert': {'queue': 'alerts'},
    # Uncomment if using non-custodial wallet system:
    # 'wallet.tasks.monitor_deposits_task': {'queue': 'deposits'},
    # 'wallet.tasks.sweep_deposits_task': {'queue': 'sweeps'},
    # 'wallet.tasks.retry_failed_sweeps_task': {'queue': 'sweeps'},
    # 'wallet.tasks.consolidate_hot_wallet_task': {'queue': 'consolidation'},
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')

