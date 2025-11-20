# OXA Pay Callback URL Status

## Current Status

✅ **Webhook endpoint exists**: `/api/v2/wallet/oxapay/webhook/`
⚠️ **Callback URL not set in settings** - auto-constructed from request

## How It Works

1. **If `OXAPAY_CALLBACK_URL` is set in settings**:
   - Uses that URL for all OXA Pay requests

2. **If not set** (current state):
   - Auto-constructs from the incoming request
   - Format: `{scheme}://{host}/api/v2/wallet/oxapay/webhook/`
   - Example: `http://localhost:8000/api/v2/wallet/oxapay/webhook/` (dev)
   - Example: `https://yourdomain.com/api/v2/wallet/oxapay/webhook/` (production)

## Is Callback URL Required?

**For static addresses**: Optional (but recommended)
**For white-label payments**: Optional (but recommended)

The callback URL is **NOT** the cause of the 401 error. The 401 is an authentication issue with the API key.

## Setting Up Callback URL

### Option 1: Add to .env file
```bash
OXAPAY_CALLBACK_URL=https://your-production-domain.com/api/v2/wallet/oxapay/webhook/
```

### Option 2: Add to Django settings.py
```python
OXAPAY_CALLBACK_URL = os.getenv('OXAPAY_CALLBACK_URL', 'https://your-domain.com/api/v2/wallet/oxapay/webhook/')
```

## Important Notes

1. **For local testing**: The auto-constructed URL won't work because OXA Pay can't reach `localhost`
   - Use a tool like ngrok to expose localhost
   - Or test without callback URL (payments will still work, just no webhook notifications)

2. **For production**: Set a fixed callback URL in settings
   - Must be publicly accessible
   - Must use HTTPS
   - Must be registered in OXA Pay dashboard (if required)

3. **Webhook endpoint is ready**: The endpoint exists and will process callbacks when OXA Pay sends them

## Testing Without Callback URL

You can test OXA Pay API calls without a callback URL. The callback is only needed for:
- Automatic payment status updates
- Real-time wallet crediting

Without callback URL:
- You can still create payments
- You'll need to manually check payment status
- Or poll the OXA Pay API for status updates

