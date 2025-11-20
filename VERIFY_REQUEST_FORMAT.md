# Request Format Verification

## Summary

All request formats have been updated to match OXA Pay's exact requirements:

### ✅ Client (`wallet/oxa_pay_client.py`)

1. **Request Method**: Uses `data=json.dumps(payload)` instead of `json=payload`
   - Matches OXA Pay documentation example exactly
   - Both `generate_white_label_payment()` and `generate_static_address()` updated

2. **auto_withdrawal Format**: Converts boolean to integer (0 or 1)
   - `True` → `1`
   - `False` → `0`
   - Matches the working test format

3. **Headers**: 
   - `merchant_api_key`: API key in header
   - `Content-Type`: `application/json`

### ✅ Views (`wallet/views_v2.py`)

1. **TopUpIntentV2ViewSet.create()**:
   - Calls `oxa_client.generate_white_label_payment()` with correct parameters
   - Passes `auto_withdrawal=True` (client converts to `1`)
   - All parameters match expected format

2. **OxaPayStaticAddressViewSet.create()**:
   - Calls `oxa_client.generate_static_address()` with correct parameters
   - Passes `auto_withdrawal=True` (client converts to `1`)
   - All parameters match expected format

### ✅ Serializers (`wallet/serializers.py`)

- **OxaPayPaymentSerializer**: Only serializes Django models to JSON for API responses
- **OxaPayStaticAddressSerializer**: Only serializes Django models to JSON for API responses
- **No changes needed**: Serializers don't make HTTP requests, they only format responses

## Request Format Example

**What gets sent to OXA Pay:**
```python
url = 'https://api.oxapay.com/v1/payment/static-address'
headers = {
    'merchant_api_key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
}
data = {
    "network": "TRON",
    "to_currency": "USDT",
    "auto_withdrawal": 0,  # Integer, not boolean
    "callback_url": "http://example.com/callback",
    "email": "user@example.com",
    "order_id": "123",
    "description": "Description"
}

response = requests.post(url, data=json.dumps(data), headers=headers)
```

**This matches the working test exactly.**

## Verification

All components are correctly formatted:
- ✅ Client uses `data=json.dumps(payload)`
- ✅ `auto_withdrawal` is integer (0 or 1)
- ✅ Headers are correct
- ✅ Views pass correct parameters
- ✅ Serializers only handle responses (no changes needed)

