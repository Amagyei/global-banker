# Transaction Monitoring Setup Guide

## Problem
Transactions sent to deposit addresses are not automatically detected and processed. This is because the `monitor_deposits` command needs to be run periodically to check the blockchain for new transactions.

## Solution
Set up automatic monitoring using one of the following methods:

### Option 1: Cron Job (Recommended for Production)

Add a cron job to run the monitoring command every 5 minutes:

```bash
# Edit crontab
crontab -e

# Add this line (runs every 5 minutes)
*/5 * * * * cd /path/to/global_banker && /path/to/venv/bin/python manage.py monitor_deposits >> /var/log/monitor_deposits.log 2>&1
```

**Example for your setup:**
```bash
*/5 * * * * cd /home/banker/banksite-1/global_banker && /home/banker/banksite-1/env/bin/python manage.py monitor_deposits >> /var/log/monitor_deposits.log 2>&1
```

### Option 2: Systemd Timer (Alternative)

Create a systemd service and timer:

**File: `/etc/systemd/system/monitor-deposits.service`**
```ini
[Unit]
Description=Monitor cryptocurrency deposits
After=network.target

[Service]
Type=oneshot
User=banker
WorkingDirectory=/home/banker/banksite-1/global_banker
Environment="PATH=/home/banker/banksite-1/env/bin"
ExecStart=/home/banker/banksite-1/env/bin/python manage.py monitor_deposits
```

**File: `/etc/systemd/system/monitor-deposits.timer`**
```ini
[Unit]
Description=Run deposit monitoring every 5 minutes
Requires=monitor-deposits.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

Then enable and start:
```bash
sudo systemctl enable monitor-deposits.timer
sudo systemctl start monitor-deposits.timer
```

### Option 3: Manual Check (For Testing)

Users can manually check payment status using the "Check Payment Status" button on the Top-Up page. This triggers the monitoring for that specific top-up intent.

### Option 4: Celery Task (For Advanced Setup)

If you're using Celery for background tasks, you can create a periodic task:

```python
# In your Celery configuration
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'monitor-deposits': {
        'task': 'wallet.tasks.monitor_deposits',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

## Verification

To verify monitoring is working:

1. **Check logs:**
   ```bash
   tail -f /var/log/monitor_deposits.log
   ```

2. **Run manually:**
   ```bash
   cd /home/banker/banksite-1/global_banker
   source ../env/bin/activate
   python manage.py monitor_deposits
   ```

3. **Check specific address:**
   ```bash
   python manage.py monitor_deposits --address tb1qtsgxt956r02czvtyqqq9tr4qvcc40s258nf5vu
   ```

## What the Monitor Does

1. Checks all active deposit addresses with pending top-ups
2. Queries the blockchain explorer (Blockstream) for transactions
3. Creates `OnChainTransaction` records for new transactions
4. Updates `TopUpIntent` status when payment is confirmed
5. Credits user's wallet balance
6. Creates `Transaction` records for accounting
7. Marks expired top-up intents

## Frequency Recommendations

- **Testnet:** Every 1-2 minutes (faster block times)
- **Mainnet:** Every 5 minutes (sufficient for most use cases)
- **High-volume:** Every 1 minute (if you have many transactions)

## Troubleshooting

### Transactions not detected

1. **Check network configuration:**
   ```bash
   python manage.py shell -c "from wallet.models import CryptoNetwork; print(CryptoNetwork.objects.all().values('key', 'is_testnet', 'explorer_api_url'))"
   ```

2. **Verify address format:**
   - Testnet addresses start with `tb1`, `m`, `n`, or `2`
   - Mainnet addresses start with `bc1`, `1`, or `3`

3. **Check explorer API:**
   ```bash
   curl https://blockstream.info/testnet/api/address/tb1qtsgxt956r02czvtyqqq9tr4qvcc40s258nf5vu/txs
   ```

4. **Review logs:**
   ```bash
   tail -100 /var/log/monitor_deposits.log
   ```

### Rate Limiting

If you hit API rate limits:
- Increase the interval between checks (e.g., every 10 minutes)
- Use a different blockchain explorer
- Implement request caching

## Notes

- The monitoring command is idempotent (safe to run multiple times)
- It only processes transactions that haven't been seen before
- Expired top-ups are automatically marked as expired
- The command respects `WALLET_TEST_MODE` setting

