# OXA Pay Payment Not Showing - Webhook Issue

## Problem

Payment to address `TXfsCNFo9MpASgWgQofqp6YS1hZpXbH1GH` (Track ID: 157800141) is not showing in your OXA Pay account because **the webhook callback URL is set to localhost**.

## Root Cause

The callback URL in the payment request is:
```
http://127.0.0.1:8000/api/v2/wallet/oxapay/webhook/
```

**OXA Pay cannot reach localhost from the internet**, so:
1. OXA Pay detects the payment on the blockchain ✅
2. OXA Pay tries to send a webhook callback ❌
3. Webhook fails because localhost is not accessible from the internet
4. Payment status remains "pending" in our database
5. Payment may show in OXA Pay dashboard but status won't update

## Solution

### Option 1: Use Production URL (Recommended)

Set `OXAPAY_CALLBACK_URL` in your `.env` file or Django settings:

```bash
OXAPAY_CALLBACK_URL=https://your-production-domain.com/api/v2/wallet/oxapay/webhook/
```

### Option 2: Use ngrok for Local Development

1. Install ngrok: `brew install ngrok` (Mac) or download from ngrok.com
2. Start ngrok: `ngrok http 8000`
3. Copy the public URL (e.g., `https://abc123.ngrok.io`)
4. Set in `.env`:
   ```bash
   OXAPAY_CALLBACK_URL=https://abc123.ngrok.io/api/v2/wallet/oxapay/webhook/
   ```

### Option 3: Check OXA Pay Dashboard Manually

1. Log into your OXA Pay dashboard
2. Search for track_id: `157800141`
3. Check the payment status there
4. If it shows "Paid" in OXA Pay but "pending" in our system, the webhook failed

## How Webhooks Work

1. **Payment Created**: System creates payment with callback URL
2. **User Sends Crypto**: Money sent to address on blockchain
3. **OXA Pay Detects**: OXA Pay monitors blockchain and detects payment
4. **Webhook Sent**: OXA Pay sends POST request to callback URL with payment status
5. **System Updates**: Our webhook handler updates payment status and credits wallet
6. **User Notified**: User receives email notification

## Current Payment Status

- **Address**: `TXfsCNFo9MpASgWgQofqp6YS1hZpXbH1GH`
- **Track ID**: `157800141`
- **Status**: `pending` (waiting for webhook)
- **Expected Amount**: 10.2 USDT
- **Created**: 2025-11-19 23:37:58
- **Expires**: 2025-11-20 00:37:58 (60 minutes)

## Verification Steps

1. **Check Blockchain**: 
   - https://tronscan.org/#/address/TXfsCNFo9MpASgWgQofqp6YS1hZpXbH1GH
   - Verify payment was sent and confirmed

2. **Check OXA Pay Dashboard**:
   - Log into OXA Pay
   - Search for track_id: `157800141`
   - Check payment status there

3. **Check Webhook Logs**:
   - Look for webhook requests in Django logs
   - Check if OXA Pay tried to send callback

4. **Manual Status Check** (if needed):
   - Use OXA Pay API to query payment status by track_id
   - Manually update payment status if webhook failed

## Next Steps

1. **Fix webhook URL** - Set `OXAPAY_CALLBACK_URL` to a public URL
2. **For existing payment** - Check OXA Pay dashboard manually
3. **For future payments** - Webhook will work once URL is fixed

## Important Notes

- **Webhooks are required** for automatic payment processing
- **Without webhooks**, payments won't be credited automatically
- **Localhost URLs don't work** - must be publicly accessible
- **OXA Pay retries webhooks** up to 5 times if they fail

