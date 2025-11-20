# OXA Pay Integration Guide

## Overview

OXA Pay integration is available as **API v2** alongside the existing non-custodial wallet system (API v1). Both systems work independently and can be used simultaneously.

- **API v1** (`/api/wallet/`): Non-custodial, full control, no fees (network fees only)
- **API v2** (`/api/v2/wallet/`): OXA Pay integration, simpler, custodial (temporary), fees apply

---

## Setup

### 1. Environment Variables

Add to your `.env` file:

```bash
# OXA Pay API Key (required for v2)
OXAPAY_API_KEY=your_merchant_api_key_here

# OXA Pay Callback URL (optional - auto-generated if not set)
OXAPAY_CALLBACK_URL=https://yourdomain.com/api/v2/wallet/oxapay/webhook/
```

### 2. Cold Wallet Address Configuration

In OXA Pay dashboard:
1. Go to **Settings** → **Address List**
2. Add your cold wallet addresses for each network
3. Enable **Auto-Withdrawal** in payment settings

This ensures funds are automatically sent to your cold wallet after payment.

---

## API Endpoints

### Base URL
- **v1 (Non-Custodial)**: `/api/wallet/`
- **v2 (OXA Pay)**: `/api/v2/wallet/`

### Authentication
Both APIs use JWT authentication (same as v1).

---

## Creating a Top-Up (v2)

### POST `/api/v2/wallet/topups/`

Create a top-up intent using OXA Pay.

**Request:**
```json
{
  "amount_minor": 10000,  // $100.00 in cents
  "network_id": "uuid-of-network",
  "use_static_address": false  // Optional: reuse static address
}
```

**Response:**
```json
{
  "topup": {
    "id": "uuid",
    "amount": "$100.00",
    "amount_minor": 10000,
    "currency_code": "USD",
    "network": {...},
    "status": "pending",
    ...
  },
  "oxapay_payment": {
    "id": "uuid",
    "track_id": "oxapay-track-id",
    "address": "bc1q...",
    "amount": 100.0,
    "pay_amount": 0.00123456,
    "pay_currency": "btc",
    "currency": "usd",
    "status": "pending",
    "qr_code": "https://...",
    "expired_at": "2024-01-01T12:00:00Z",
    ...
  }
}
```

**Features:**
- ✅ Automatic address generation via OXA Pay
- ✅ QR code for easy payment
- ✅ Expiration time (60 minutes default)
- ✅ Auto-withdrawal to cold wallet
- ✅ Webhook notifications

---

## Static Addresses (v2)

### POST `/api/v2/wallet/oxapay/static-addresses/`

Create a reusable static address for a network.

**Request:**
```json
{
  "network_id": "uuid-of-network"
}
```

**Response:**
```json
{
  "id": "uuid",
  "track_id": "oxapay-track-id",
  "network": {...},
  "address": "bc1q...",
  "qr_code": "https://...",
  "is_active": true,
  ...
}
```

**Use Case:**
- Reuse the same address for multiple payments
- No expiration (until 6 months of inactivity)
- Useful for recurring payments

### GET `/api/v2/wallet/oxapay/static-addresses/`

List all static addresses for the authenticated user.

---

## Payment Status (v2)

### GET `/api/v2/wallet/oxapay/payments/`

List all OXA Pay payments for the authenticated user.

**Query Parameters:**
- `status`: Filter by status (`pending`, `paid`, `expired`, `failed`)
- `network`: Filter by network ID

**Response:**
```json
[
  {
    "id": "uuid",
    "track_id": "oxapay-track-id",
    "address": "bc1q...",
    "amount": 100.0,
    "pay_amount": 0.00123456,
    "pay_currency": "btc",
    "status": "paid",
    "is_expired": false,
    ...
  }
]
```

---

## Webhook Configuration

### Webhook Endpoint
`POST /api/v2/wallet/oxapay/webhook/`

OXA Pay will send payment notifications to this endpoint.

**Webhook Payload:**
```json
{
  "track_id": "oxapay-track-id",
  "status": "paid",
  "amount": 100.0,
  "pay_amount": 0.00123456,
  "pay_currency": "btc",
  "currency": "usd",
  "tx_hash": "abc123...",
  "network": "Bitcoin Network",
  "address": "bc1q...",
  "order_id": "uuid",
  ...
}
```

**What Happens:**
1. Webhook receives payment notification
2. System verifies signature (if provided)
3. Updates `OxaPayPayment` status
4. If status is `paid`:
   - Credits user's wallet
   - Updates `TopUpIntent` to `succeeded`
   - Creates `Transaction` record

**Security:**
- Signature verification (HMAC-SHA256)
- CSRF exempt (webhook endpoint)
- Duplicate prevention (checks existing transactions)

---

## Comparison: v1 vs v2

| Feature | v1 (Non-Custodial) | v2 (OXA Pay) |
|---------|-------------------|--------------|
| **Address Generation** | Derived from master xpub | OXA Pay generates |
| **Blockchain Monitoring** | We poll Blockstream API | OXA Pay handles |
| **Sweep Service** | We control private keys | OXA Pay handles |
| **Hot Wallet** | ✅ Our encrypted xprv | ❌ Their wallet |
| **Cold Wallet** | ✅ Our address | ✅ Auto-withdrawal |
| **Private Key Control** | ✅ Full control | ❌ They control |
| **Fees** | Network fees only | OXA Pay fees + network |
| **Complexity** | High (we manage) | Low (they manage) |
| **Reliability** | Our responsibility | Their infrastructure |
| **Customization** | Full control | Limited |

---

## Frontend Integration

### Example: Create Top-Up with OXA Pay

```typescript
// Use v2 API instead of v1
const response = await api.post('/api/v2/wallet/topups/', {
  amount_minor: 10000,  // $100.00
  network_id: networkId,
  use_static_address: false
});

const { topup, oxapay_payment } = response.data;

// Display payment address and QR code
console.log('Address:', oxapay_payment.address);
console.log('QR Code:', oxapay_payment.qr_code);
console.log('Amount:', oxapay_payment.pay_amount, oxapay_payment.pay_currency);
console.log('Expires:', oxapay_payment.expired_at);
```

### Example: Check Payment Status

```typescript
// Poll payment status
const checkStatus = async (trackId: string) => {
  const response = await api.get(`/api/v2/wallet/oxapay/payments/?track_id=${trackId}`);
  const payment = response.data[0];
  
  if (payment.status === 'paid') {
    // Payment successful, wallet credited
    console.log('Payment confirmed!');
  } else if (payment.status === 'expired') {
    // Payment expired
    console.log('Payment expired');
  }
};
```

---

## Error Handling

### Common Errors

1. **`OXAPAY_API_KEY must be set`**
   - Solution: Add `OXAPAY_API_KEY` to `.env`

2. **`Failed to create OXA Pay payment`**
   - Check OXA Pay API key validity
   - Verify network name mapping
   - Check OXA Pay dashboard for errors

3. **`Payment not found`** (webhook)
   - Payment may have been created outside the system
   - Check `track_id` matches

4. **`Invalid signature`** (webhook)
   - Verify `X-OxaPay-Signature` header
   - Check API key matches

---

## Testing

### Test Mode

OXA Pay supports sandbox mode. Set in request:

```json
{
  "sandbox": true
}
```

**Note:** Currently not implemented in our integration. Add to `oxa_pay_client.py` if needed.

### Manual Testing

1. Create a top-up via v2 API
2. Send test payment to the generated address
3. Check webhook receives notification
4. Verify wallet is credited
5. Check transaction record created

---

## Migration from v1 to v2

### For Existing Users

Users can switch between v1 and v2 at any time:

1. **v1**: Direct crypto deposits (non-custodial)
2. **v2**: OXA Pay payments (custodial, simpler)

Both credit the same `Wallet` model, so balances are shared.

### For New Users

- **Default**: Use v1 (non-custodial, no fees)
- **Alternative**: Offer v2 (OXA Pay, simpler flow)

---

## Admin Interface

OXA Pay models are available in Django admin:

- **OxaPayPayment**: View all payments, status, amounts
- **OxaPayStaticAddress**: Manage static addresses

**Location:** `/admin/wallet/oxapaypayment/`

---

## Security Considerations

1. **API Key Storage**
   - Store `OXAPAY_API_KEY` in environment variables
   - Never commit to version control

2. **Webhook Security**
   - Signature verification (implemented)
   - CSRF exempt (required for webhooks)
   - Rate limiting (consider adding)

3. **Cold Wallet**
   - Configure in OXA Pay dashboard
   - Keep private keys offline
   - Monitor auto-withdrawals

---

## Troubleshooting

### Payments Not Crediting

1. Check webhook is receiving callbacks:
   ```bash
   # Check Django logs
   tail -f logs/django.log | grep oxapay
   ```

2. Verify webhook URL is correct in OXA Pay dashboard

3. Check `OxaPayPayment` status in admin

4. Verify signature verification (if enabled)

### Address Generation Failing

1. Check `OXAPAY_API_KEY` is valid
2. Verify network name mapping (Bitcoin Network, Ethereum Network, etc.)
3. Check OXA Pay API status

---

## Next Steps

1. ✅ OXA Pay integration complete
2. ⏳ Frontend integration (update API calls to use v2)
3. ⏳ Testing with real OXA Pay account
4. ⏳ Production deployment

---

## Support

- **OXA Pay Docs**: https://docs.oxapay.com
- **OXA Pay Dashboard**: https://merchant.oxapay.com
- **Our System**: Check Django admin for payment records

