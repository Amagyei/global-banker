# Robust Blockchain Monitoring System Guide

## Overview

The monitoring system has been enhanced with:
- ✅ **Retry logic** with exponential backoff
- ✅ **Circuit breaker** pattern to prevent cascading failures
- ✅ **Rate limiting** to respect API limits
- ✅ **Health checks** before monitoring
- ✅ **Automatic pending transaction updates**
- ✅ **Comprehensive error handling** and logging
- ✅ **Testnet and mainnet support**

## Features

### 1. **Retry Logic**
- Automatically retries failed requests (default: 3 attempts)
- Exponential backoff: 1s, 2s, 4s delays
- Handles timeouts, connection errors, and server errors (5xx)

### 2. **Circuit Breaker**
- Opens circuit after 5 consecutive failures
- Prevents overwhelming failing APIs
- Auto-recovery after 60 seconds
- Half-open state for gradual recovery

### 3. **Rate Limiting**
- Minimum 500ms between requests
- Respects API rate limits
- Handles 429 (Too Many Requests) responses

### 4. **Health Checks**
- Verifies API connectivity before monitoring
- Can skip unhealthy networks
- Reports current block height

### 5. **Pending Transaction Updates**
- Automatically updates existing pending transactions
- Checks for new confirmations
- Processes confirmed transactions

## Usage

### Basic Monitoring

```bash
# Monitor all active networks
python manage.py monitor_deposits

# Monitor specific network
python manage.py monitor_deposits --network btc

# Monitor specific address
python manage.py monitor_deposits --address tb1qtsgxt956r02czvtyqqq9tr4qvcc40s258nf5vu
```

### With Health Checks

```bash
# Run health check before monitoring
python manage.py monitor_deposits --health-check

# Skip unhealthy networks
python manage.py monitor_deposits --health-check --skip-healthy
```

### Disable Pending Updates

```bash
# Don't update existing pending transactions (only check for new ones)
python manage.py monitor_deposits --no-update-pending
```

## Setting Up Cron Job

### For Production (Every 5 Minutes)

```bash
# Edit crontab
crontab -e

# Add this line (adjust path as needed)
*/5 * * * * cd /path/to/global_banker && /path/to/venv/bin/python manage.py monitor_deposits >> /var/log/wallet_monitoring.log 2>&1
```

### For Development (Every 1 Minute)

```bash
* * * * * cd /path/to/global_banker && /path/to/venv/bin/python manage.py monitor_deposits --health-check >> /var/log/wallet_monitoring.log 2>&1
```

### With Health Checks and Error Alerts

```bash
*/5 * * * * cd /path/to/global_banker && /path/to/venv/bin/python manage.py monitor_deposits --health-check --skip-healthy || echo "Monitoring failed at $(date)" | mail -s "Wallet Monitoring Alert" admin@example.com
```

## Error Handling

### Automatic Retries
- **Timeout errors**: Retried with exponential backoff
- **Connection errors**: Retried up to 3 times
- **Server errors (5xx)**: Retried with backoff
- **Client errors (4xx)**: Not retried (logged as error)

### Circuit Breaker States
1. **Closed**: Normal operation
2. **Open**: Too many failures, requests blocked
3. **Half-Open**: Testing if service recovered

### Error Logging
All errors are logged with:
- Full stack traces
- Transaction/address context
- Error type and message
- Timestamp

## Monitoring Output

### Success Example
```
Monitoring Bitcoin (btc)...
  Network type: testnet
  ✓ Updated 2 pending transaction(s) for tb1qtsgxt956r02cz...
  ✓ Found new transaction for tb1qtsgxt956r02cz...

============================================================
Monitoring Summary:
  Addresses checked: 3
  New transactions found: 1
  Pending transactions updated: 2
  Errors: 0
  Expired top-ups: 0
============================================================
```

### With Errors
```
Monitoring Bitcoin (btc)...
  Network type: testnet
  ✗ Monitoring error for tb1qtsgxt956r02cz...: API timeout

============================================================
Monitoring Summary:
  Addresses checked: 3
  New transactions found: 0
  Pending transactions updated: 1
  Errors: 1
  Expired top-ups: 0
============================================================
```

## Health Check Output

```
Running health checks...
  ✓ Bitcoin: API healthy, current block height: 4782717
  ✗ Ethereum: API unhealthy: Connection timeout

Monitoring Bitcoin (btc)...
  Network type: testnet
  ...
```

## Configuration

### Environment Variables

```bash
# Enable testnet mode
WALLET_TEST_MODE=True

# Set default xpub
DEFAULT_XPUB=your_xpub_here
```

### Network Settings

Networks are configured in the database via `CryptoNetwork` model:
- `is_testnet`: Network type
- `explorer_api_url`: API endpoint
- `required_confirmations`: Confirmations needed (default: 2)
- `is_active`: Enable/disable monitoring

## Best Practices

### 1. **Run Health Checks in Production**
```bash
python manage.py monitor_deposits --health-check --skip-healthy
```

### 2. **Monitor Logs Regularly**
```bash
tail -f /var/log/wallet_monitoring.log
```

### 3. **Set Up Alerts**
- Monitor error rates
- Alert on circuit breaker opens
- Alert on API health check failures

### 4. **Adjust Retry Settings**
If you need different retry behavior, modify `RobustBlockchainMonitor`:
```python
monitor = RobustBlockchainMonitor(
    network,
    max_retries=5,        # More retries
    retry_delay=2,         # Longer initial delay
    backoff_factor=2      # Exponential backoff
)
```

### 5. **Rate Limiting**
If API has strict rate limits, increase `min_request_interval`:
```python
monitor.min_request_interval = 1.0  # 1 second between requests
```

## Troubleshooting

### Circuit Breaker Stuck Open
- Check API health: `python manage.py monitor_deposits --health-check`
- Wait 60 seconds for auto-recovery
- Check network connectivity

### High Error Rate
- Check API endpoint URLs
- Verify network settings (testnet/mainnet)
- Check API rate limits
- Review logs for specific errors

### Transactions Not Updating
- Verify transactions exist on blockchain
- Check address format (testnet vs mainnet)
- Run with `--update-pending` flag
- Check logs for errors

### Performance Issues
- Increase `min_request_interval` for rate limiting
- Reduce number of addresses monitored
- Use `--network` to monitor specific networks
- Check database query performance

## Testing

### Test Health Check
```bash
python manage.py monitor_deposits --health-check
```

### Test Specific Address
```bash
python manage.py monitor_deposits --address tb1qtsgxt956r02czvtyqqq9tr4qvcc40s258nf5vu
```

### Test Error Handling
Temporarily break API URL in database to test circuit breaker.

## Production Checklist

- [ ] Cron job configured (every 5 minutes)
- [ ] Health checks enabled
- [ ] Log rotation configured
- [ ] Error alerting set up
- [ ] Monitoring logs reviewed regularly
- [ ] Backup monitoring system (optional)
- [ ] Rate limits configured
- [ ] Network settings verified (testnet/mainnet)

## Support

For issues or questions:
1. Check logs: `/var/log/wallet_monitoring.log`
2. Run health check: `python manage.py monitor_deposits --health-check`
3. Review error messages in logs
4. Verify network configuration in database

