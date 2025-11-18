# Wallet Setup Guide

## What You Need to Provide

### 1. Extended Public Key (xpub)

**What it is**: An extended public key that allows generating unlimited Bitcoin addresses without exposing your private key.

**How to get it**:
- Use a hardware wallet (Ledger, Trezor) or software wallet (Electrum, Bitcoin Core)
- Export the xpub for the account you want to use
- Format: Usually starts with `xpub` (mainnet) or `tpub` (testnet)

**Where to set it**:
```bash
# In your .env file or environment variables
export DEFAULT_XPUB="xpub6C..."  # Your actual xpub here
```

**Security**: 
- ✅ Safe to store on server (it's public)
- ❌ Never store the extended private key (xprv) on the server
- 🔒 In production, consider encrypting this value

### 2. Test Mode Configuration

**For Development**:
```bash
export WALLET_TEST_MODE="True"  # Uses mock addresses, no real blockchain
```

**For Production**:
```bash
export WALLET_TEST_MODE="False"  # Uses real blockchain addresses
```

### 3. Redis Configuration (Optional but Recommended)

**For Development**:
```bash
# Install Redis locally
# macOS: brew install redis
# Linux: sudo apt-get install redis-server

# Start Redis
redis-server

# Redis URL (default, can be omitted)
export REDIS_URL="redis://127.0.0.1:6379/1"
```

**For Production**:
```bash
# Use managed Redis service (AWS ElastiCache, Redis Cloud, etc.)
export REDIS_URL="redis://your-redis-host:6379/1"
# Or with password:
export REDIS_URL="redis://:password@your-redis-host:6379/1"
```

---

## What is CoinGecko Used For?

**CoinGecko** is a cryptocurrency price API that provides real-time exchange rates.

### Purpose:
- **Converts cryptocurrency to USD**: When a user deposits Bitcoin/Ethereum, we need to know how much USD it's worth
- **Example**: User deposits 0.001 BTC → CoinGecko tells us BTC is worth $50,000 → We credit $50.00 USD to their wallet

### How It Works:
1. User creates a top-up intent for $20 USD
2. User sends 0.0004 BTC to the deposit address
3. Our system detects the transaction
4. We query CoinGecko: "What's 1 BTC worth in USD?"
5. CoinGecko responds: "$50,000"
6. We calculate: 0.0004 BTC × $50,000 = $20 USD
7. We credit $20.00 to the user's wallet

### API Details:
- **Free Tier**: 10-50 calls per minute (sufficient for most use cases)
- **No API Key Required**: For basic usage
- **Caching**: Exchange rates are cached for 5 minutes to reduce API calls
- **Fallback**: If API fails, uses cached value or safe defaults

### Alternative APIs:
If you prefer a different service:
- **CoinMarketCap**: Requires API key, higher rate limits
- **Binance API**: Free, good for major cryptocurrencies
- **CryptoCompare**: Free tier available

To switch, modify `wallet/exchange_rates.py` → `_fetch_exchange_rate_from_api()`

---

## Installation Requirements

### Python Packages:
```bash
pip install bip-utils  # For address derivation
pip install django-redis  # For Redis cache (optional but recommended)
pip install requests  # Already installed, but needed for exchange rates
```

### System Requirements:
- **Redis**: For caching exchange rates (recommended)
  ```bash
  # macOS
  brew install redis
  brew services start redis
  
  # Ubuntu/Debian
  sudo apt-get install redis-server
  sudo systemctl start redis
  ```

---

## Environment Variables Summary

Create a `.env` file in your project root:

```bash
# Required for Production
DEFAULT_XPUB=xpub6C...your-xpub-here

# Test Mode (True for dev, False for production)
WALLET_TEST_MODE=True

# Redis (optional, defaults to localhost)
REDIS_URL=redis://127.0.0.1:6379/1

# Database (if using Postgres)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

---

## Quick Start Checklist

### Development:
- [ ] Install Redis: `brew install redis` or `apt-get install redis-server`
- [ ] Start Redis: `redis-server` or `brew services start redis`
- [ ] Set `WALLET_TEST_MODE=True` in environment
- [ ] Install Python packages: `pip install bip-utils django-redis`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Test: Create a top-up intent and check if it works

### Production:
- [ ] Set `DEFAULT_XPUB` with your actual xpub
- [ ] Set `WALLET_TEST_MODE=False`
- [ ] Set up Redis (managed service recommended)
- [ ] Set `REDIS_URL` to your Redis instance
- [ ] Set up cron job for `monitor_deposits` command:
  ```bash
  # Run every 5 minutes
  */5 * * * * cd /path/to/project && source venv/bin/activate && python manage.py monitor_deposits
  ```
- [ ] Monitor CoinGecko API usage (stay within free tier limits)
- [ ] Set up logging/monitoring for exchange rate failures

---

## Testing the Setup

### 1. Test Exchange Rate API:
```python
# In Django shell: python manage.py shell
from wallet.exchange_rates import get_exchange_rate

# Get BTC/USD rate
rate = get_exchange_rate('BTC', 'USD')
print(f"1 BTC = ${rate} USD")
```

### 2. Test Address Derivation:
```python
# In Django shell
from wallet.utils import derive_address_from_xpub

xpub = "your-xpub-here"
address = derive_address_from_xpub(xpub, 0, "btc", is_testnet=True)
print(f"First address: {address}")
```

### 3. Test Top-Up Flow:
1. Create a top-up intent via API
2. Get the deposit address
3. In test mode: Run `python manage.py monitor_deposits` to simulate deposit
4. Check wallet balance was credited

---

## Troubleshooting

### "Address derivation error"
- **Cause**: Missing or invalid xpub
- **Fix**: Set `DEFAULT_XPUB` environment variable with valid xpub

### "Exchange rate API failed"
- **Cause**: CoinGecko API rate limit or network issue
- **Fix**: System will use cached value or fallback rate

### "Redis connection failed"
- **Cause**: Redis not running or wrong URL
- **Fix**: Start Redis server or check `REDIS_URL`

### "bip_utils not found"
- **Cause**: Package not installed
- **Fix**: `pip install bip-utils`

---

## Security Notes

1. **Never commit xpub to version control** - Use environment variables
2. **Never store xprv (private key)** - Only xpub is needed
3. **Encrypt xpub in production** - Consider using Django's encrypted fields or secret manager
4. **Monitor API usage** - CoinGecko has rate limits
5. **Use HTTPS** - All API calls should be over HTTPS
6. **Validate addresses** - Always validate derived addresses before using

---

## Next Steps

1. **Get your xpub** from your wallet
2. **Set environment variables**
3. **Install dependencies** (`bip-utils`, `django-redis`)
4. **Start Redis**
5. **Test the integration**
6. **Set up monitoring** for production

For detailed implementation, see `WALLET_DEVELOPMENT_MANUAL.md`.

