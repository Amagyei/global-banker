# Top-Up Validation System Testing Guide

Complete guide for testing the OXA Pay top-up validation system, including frontend, backend, webhooks, and edge cases.

---

## 📋 **Testing Overview**

The top-up validation system includes:
1. **Frontend Validation**: Amount, network selection, UI feedback
2. **Backend API Validation**: Request validation, OXA Pay integration
3. **Webhook Validation**: HMAC signature, payment status updates
4. **Payment Processing**: Wallet crediting, transaction creation
5. **Error Handling**: Failed payments, expired payments, invalid requests

---

## 🧪 **1. Frontend Testing**

### Test Cases

#### 1.1 Network Selection
```bash
# Test: Load networks and verify only mainnet networks are shown
# Expected: Only BTC, ETH, USDT, USDC, BNB, SOL, LTC (mainnet) appear
```

**Steps:**
1. Navigate to `/top-up`
2. Verify network buttons are displayed
3. Verify testnet networks are NOT shown
4. Click each network button
5. Verify selected network is highlighted

**Expected Results:**
- ✅ Only 7 supported networks shown (BTC, ETH, USDT, USDC, BNB, SOL, LTC)
- ✅ No testnet networks visible
- ✅ Network selection updates correctly

---

#### 1.2 Amount Validation
```bash
# Test: Validate amount input
```

**Test Cases:**

| Input | Expected Behavior |
|-------|-------------------|
| Empty | Button disabled |
| 0 | Button disabled or error |
| Negative | Button disabled or error |
| < 10 | Error: "Minimum amount is $10" |
| 10 | ✅ Valid |
| 100 | ✅ Valid |
| 1000 | ✅ Valid |
| Non-numeric | Button disabled or error |
| Decimal (10.50) | ✅ Valid |

**Steps:**
1. Select a network
2. Enter various amounts in custom amount field
3. Verify button state and error messages

---

#### 1.3 Quick Amount Buttons
```bash
# Test: Quick top-up buttons ($10, $25, $50, $100, $500)
```

**Steps:**
1. Select a network
2. Click each quick amount button
3. Verify payment creation is triggered
4. Verify loading state during creation

**Expected Results:**
- ✅ Each button triggers top-up creation
- ✅ Loading spinner appears
- ✅ Payment details card appears after creation

---

#### 1.4 Payment Details Display
```bash
# Test: Verify payment details are displayed correctly
```

**Steps:**
1. Create a top-up
2. Verify payment card appears with:
   - QR code (if available)
   - Deposit address
   - Amount to pay
   - Currency
   - Status badge
   - Expiration countdown
   - Track ID

**Expected Results:**
- ✅ All payment details visible
- ✅ QR code is clickable/copyable
- ✅ Address is copyable
- ✅ Countdown updates every second
- ✅ Status badge shows correct color

---

#### 1.5 Payment Status Check
```bash
# Test: Manual status check button
```

**Steps:**
1. Create a top-up with status "pending"
2. Click "Check Payment Status" button
3. Verify status updates if payment changed

**Expected Results:**
- ✅ Button triggers API call
- ✅ Status updates if payment changed
- ✅ Loading state during check

---

## 🔌 **2. Backend API Testing**

### 2.1 Create Top-Up Intent

#### Valid Request
```bash
# Test: Create top-up with valid data
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000,
    "network_id": "NETWORK_UUID",
    "use_static_address": false
  }'
```

**Expected Response (201 Created):**
```json
{
  "topup": {
    "id": "...",
    "amount_minor": 1000,
    "currency_code": "USD",
    "status": "pending",
    "network": {...},
    "created_at": "..."
  },
  "payment": {
    "track_id": "...",
    "address": "bc1q...",
    "qr_code": "https://...",
    "amount": 10.0,
    "pay_amount": 0.00012345,
    "pay_currency": "btc",
    "status": "pending",
    "expired_at": 1234567890
  }
}
```

---

#### Invalid Requests

**Test Case 1: Missing amount_minor**
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "network_id": "NETWORK_UUID"
  }'
```

**Expected:** `400 Bad Request` - `"amount_minor and network_id are required"`

---

**Test Case 2: Missing network_id**
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000
  }'
```

**Expected:** `400 Bad Request` - `"amount_minor and network_id are required"`

---

**Test Case 3: Invalid amount (zero)**
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 0,
    "network_id": "NETWORK_UUID"
  }'
```

**Expected:** `400 Bad Request` - `"amount_minor must be a positive integer"`

---

**Test Case 4: Invalid amount (negative)**
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": -100,
    "network_id": "NETWORK_UUID"
  }'
```

**Expected:** `400 Bad Request` - `"amount_minor must be a positive integer"`

---

**Test Case 5: Invalid network_id**
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000,
    "network_id": "invalid-uuid"
  }'
```

**Expected:** `404 Not Found` - `"Network not found"`

---

**Test Case 6: Inactive network**
```bash
# Use a network with is_active=False
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000,
    "network_id": "INACTIVE_NETWORK_UUID"
  }'
```

**Expected:** `404 Not Found` - `"Network not found"`

---

**Test Case 7: Unauthenticated request**
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000,
    "network_id": "NETWORK_UUID"
  }'
```

**Expected:** `401 Unauthorized`

---

### 2.2 List Top-Up Intents

```bash
# Test: Get user's top-up history
curl -X GET http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "count": 5,
  "results": [
    {
      "id": "...",
      "amount_minor": 1000,
      "status": "succeeded",
      "network": {...},
      "created_at": "..."
    },
    ...
  ]
}
```

---

### 2.3 Get Payment Details

```bash
# Test: Get payment by track_id
curl -X GET http://localhost:8000/api/v2/wallet/payments/?track_id=TRACK_ID \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "count": 1,
  "results": [
    {
      "track_id": "...",
      "address": "bc1q...",
      "status": "pending",
      "amount": 10.0,
      ...
    }
  ]
}
```

---

### 2.4 Get Accepted Currencies

```bash
# Test: Get list of accepted currencies
curl -X GET http://localhost:8000/api/v2/wallet/payments/accepted_currencies/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "currencies": ["BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "LTC"]
}
```

---

## 🔔 **3. Webhook Testing**

### 3.1 Webhook Endpoint Test

```bash
# Test: Verify webhook endpoint is accessible
curl -X POST http://localhost:8000/api/v2/wallet/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Expected:** `200 OK` with body `"OK"` (even for invalid requests, to prevent retries)

---

### 3.2 HMAC Signature Validation

#### Valid HMAC Test
```python
# test_webhook_hmac.py
import hmac
import hashlib
import json
import requests

# OXA Pay webhook payload
payload = {
    "track_id": "123456789",
    "status": "Paid",
    "type": "white_label",
    "amount": 10.0,
    "value": 0.00012345,
    "currency": "BTC",
    "txs": [{
        "status": "confirmed",
        "tx_hash": "abc123...",
        "sent_amount": 10.0,
        "received_amount": 9.95,
        "currency": "BTC",
        "network": "Bitcoin Network",
        "address": "bc1q...",
        "confirmations": 6
    }]
}

# Calculate HMAC
api_key = "YOUR_OXAPAY_API_KEY"
body = json.dumps(payload)
hmac_signature = hmac.new(
    api_key.encode('utf-8'),
    body.encode('utf-8'),
    hashlib.sha512
).hexdigest()

# Send webhook
response = requests.post(
    "http://localhost:8000/api/v2/wallet/webhook/",
    json=payload,
    headers={"HMAC": hmac_signature}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

**Expected:** `200 OK` with body `"OK"`

---

#### Invalid HMAC Test
```python
# Test with wrong HMAC
response = requests.post(
    "http://localhost:8000/api/v2/wallet/webhook/",
    json=payload,
    headers={"HMAC": "invalid_signature"}
)

# Expected: 400 Bad Request (in production)
# In development: May log warning but still return 200
```

---

### 3.3 Payment Status Updates

#### Test: "Paying" Status
```python
# Simulate "Paying" webhook (payment sent, awaiting confirmation)
payload = {
    "track_id": "123456789",
    "status": "Paying",
    "type": "white_label",
    "amount": 10.0,
    "txs": [{
        "status": "confirming",
        "tx_hash": "abc123...",
        "confirmations": 1
    }]
}

# Send webhook
# Expected: Payment status updated to "paying", wallet NOT credited yet
```

---

#### Test: "Paid" Status
```python
# Simulate "Paid" webhook (payment confirmed)
payload = {
    "track_id": "123456789",
    "status": "Paid",
    "type": "white_label",
    "amount": 10.0,
    "txs": [{
        "status": "confirmed",
        "tx_hash": "abc123...",
        "confirmations": 6
    }]
}

# Send webhook
# Expected:
# 1. Payment status updated to "paid"
# 2. Top-up intent status updated to "succeeded"
# 3. User wallet credited with $10.00
# 4. Transaction record created
# 5. Email notification sent
```

**Verification:**
```bash
# Check wallet balance
curl -X GET http://localhost:8000/api/v2/wallet/wallet/ \
  -H "Authorization: Bearer TOKEN"

# Check transactions
curl -X GET http://localhost:8000/api/transactions/ \
  -H "Authorization: Bearer TOKEN"
```

---

#### Test: "Failed" Status
```python
# Simulate "Failed" webhook
payload = {
    "track_id": "123456789",
    "status": "Failed",
    "type": "white_label",
    "amount": 10.0
}

# Expected:
# 1. Payment status updated to "failed"
# 2. Top-up intent status updated to "failed"
# 3. Wallet NOT credited
# 4. Email notification sent
```

---

#### Test: "Expired" Status
```python
# Simulate "Expired" webhook
payload = {
    "track_id": "123456789",
    "status": "Expired",
    "type": "white_label",
    "amount": 10.0
}

# Expected:
# 1. Payment status updated to "expired"
# 2. Top-up intent status updated to "expired"
# 3. Wallet NOT credited
# 4. Email notification sent
```

---

### 3.4 Webhook Test Endpoint

```bash
# Use the test webhook endpoint (admin only)
curl -X POST http://localhost:8000/api/v2/wallet/webhook/test/ \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track_id": "123456789",
    "status": "Paid",
    "amount": 10.0
  }'
```

**Expected:** Test webhook processing without actual OXA Pay call

---

## 🧩 **4. Edge Cases & Error Scenarios**

### 4.1 Duplicate Payment Crediting

**Test:** Prevent double crediting if webhook is called twice

```python
# Send "Paid" webhook twice for same track_id
payload = {
    "track_id": "123456789",
    "status": "Paid",
    "amount": 10.0
}

# Send first time
requests.post(webhook_url, json=payload, headers=headers)
# Expected: Wallet credited with $10.00

# Send second time (duplicate)
requests.post(webhook_url, json=payload, headers=headers)
# Expected: 
# - Log: "Payment already credited, skipping duplicate"
# - Wallet balance unchanged
# - No duplicate transaction created
```

---

### 4.2 Missing Track ID

```python
# Webhook without track_id
payload = {
    "status": "Paid",
    "amount": 10.0
}

# Expected: 400 Bad Request - "Missing track_id"
```

---

### 4.3 Payment Not Found

```python
# Webhook for non-existent payment
payload = {
    "track_id": "nonexistent",
    "status": "Paid",
    "amount": 10.0
}

# Expected: 
# - Log: "Payment not found for track_id: nonexistent"
# - Return 200 OK (to prevent OXA Pay retries)
# - No wallet credit
```

---

### 4.4 Invalid JSON

```bash
# Send invalid JSON
curl -X POST http://localhost:8000/api/v2/wallet/webhook/ \
  -H "Content-Type: application/json" \
  -d 'invalid json'

# Expected: 400 Bad Request - "Invalid JSON"
```

---

### 4.5 Network Mismatch

**Test:** Payment for wrong network

```bash
# Create top-up for BTC
# Receive webhook for ETH payment
# Expected: Payment still processed (OXA Pay handles network)
```

---

### 4.6 Amount Mismatch

**Test:** Webhook amount differs from top-up amount

```python
# Top-up created for $10.00
# Webhook reports $9.50
# Expected: Use webhook amount (source of truth)
```

---

### 4.7 OXA Pay API Errors

**Test:** OXA Pay API returns error during top-up creation

```bash
# Simulate OXA Pay API failure
# Expected: 
# - 500 Internal Server Error
# - Error logged
# - Top-up intent created but status = "pending"
# - No payment record created
```

---

## 🔄 **5. Integration Testing**

### 5.1 Complete Flow Test

**End-to-End Test:**

1. **Create Top-Up**
   ```bash
   curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
     -H "Authorization: Bearer TOKEN" \
     -d '{"amount_minor": 1000, "network_id": "BTC_NETWORK_ID"}'
   ```

2. **Verify Payment Created**
   ```bash
   curl -X GET http://localhost:8000/api/v2/wallet/payments/?track_id=TRACK_ID \
     -H "Authorization: Bearer TOKEN"
   ```

3. **Simulate Payment (Webhook)**
   ```python
   # Send "Paying" webhook
   # Wait a few seconds
   # Send "Paid" webhook
   ```

4. **Verify Wallet Credited**
   ```bash
   curl -X GET http://localhost:8000/api/v2/wallet/wallet/ \
     -H "Authorization: Bearer TOKEN"
   # Expected: balance_minor increased by 1000
   ```

5. **Verify Transaction Created**
   ```bash
   curl -X GET http://localhost:8000/api/transactions/ \
     -H "Authorization: Bearer TOKEN"
   # Expected: New credit transaction with category="topup"
   ```

---

### 5.2 Multiple Concurrent Top-Ups

**Test:** Create multiple top-ups simultaneously

```bash
# Create 3 top-ups at once
for i in {1..3}; do
  curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
    -H "Authorization: Bearer TOKEN" \
    -d "{\"amount_minor\": $((i*1000)), \"network_id\": \"BTC_NETWORK_ID\"}" &
done
wait

# Expected:
# - All 3 top-ups created successfully
# - Each has unique track_id
# - Each has unique address
```

---

## 🧪 **6. Automated Testing Scripts**

### 6.1 Python Test Script

```python
# test_topup_validation.py
import requests
import json
import time
import hmac
import hashlib

BASE_URL = "http://localhost:8000"
TOKEN = "YOUR_ACCESS_TOKEN"
API_KEY = "YOUR_OXAPAY_API_KEY"

def test_create_topup():
    """Test creating a top-up"""
    url = f"{BASE_URL}/api/v2/wallet/topups/"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = {
        "amount_minor": 1000,
        "network_id": "BTC_NETWORK_UUID",
        "use_static_address": False
    }
    
    response = requests.post(url, json=data, headers=headers)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    
    result = response.json()
    assert "topup" in result
    assert "payment" in result
    assert result["payment"]["track_id"]
    assert result["payment"]["address"]
    
    print("✅ Top-up created successfully")
    return result["payment"]["track_id"]

def test_webhook_paid(track_id):
    """Test webhook with Paid status"""
    url = f"{BASE_URL}/api/v2/wallet/webhook/"
    
    payload = {
        "track_id": track_id,
        "status": "Paid",
        "type": "white_label",
        "amount": 10.0,
        "value": 0.00012345,
        "currency": "BTC",
        "txs": [{
            "status": "confirmed",
            "tx_hash": "test_hash_123",
            "sent_amount": 10.0,
            "received_amount": 9.95,
            "currency": "BTC",
            "network": "Bitcoin Network",
            "address": "bc1qtest",
            "confirmations": 6
        }]
    }
    
    # Calculate HMAC
    body = json.dumps(payload)
    hmac_sig = hmac.new(
        API_KEY.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    headers = {"HMAC": hmac_sig}
    response = requests.post(url, json=payload, headers=headers)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.text == "OK"
    
    print("✅ Webhook processed successfully")
    time.sleep(1)  # Wait for async processing

def test_wallet_balance():
    """Verify wallet was credited"""
    url = f"{BASE_URL}/api/v2/wallet/wallet/"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    response = requests.get(url, headers=headers)
    assert response.status_code == 200
    
    wallet = response.json()[0]
    print(f"✅ Wallet balance: ${wallet['balance_minor'] / 100:.2f}")
    return wallet

if __name__ == "__main__":
    print("🧪 Testing Top-Up Validation System\n")
    
    # Test 1: Create top-up
    track_id = test_create_topup()
    
    # Test 2: Simulate payment webhook
    test_webhook_paid(track_id)
    
    # Test 3: Verify wallet credited
    wallet = test_wallet_balance()
    
    print("\n✅ All tests passed!")
```

---

### 6.2 Bash Test Script

```bash
#!/bin/bash
# test_topup.sh

BASE_URL="http://localhost:8000"
TOKEN="YOUR_ACCESS_TOKEN"

echo "🧪 Testing Top-Up Validation System"
echo ""

# Test 1: Create top-up
echo "1. Creating top-up..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v2/wallet/topups/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000,
    "network_id": "BTC_NETWORK_UUID"
  }')

TRACK_ID=$(echo $RESPONSE | jq -r '.payment.track_id')
ADDRESS=$(echo $RESPONSE | jq -r '.payment.address')

if [ -z "$TRACK_ID" ] || [ "$TRACK_ID" == "null" ]; then
  echo "❌ Failed to create top-up"
  exit 1
fi

echo "✅ Top-up created: track_id=$TRACK_ID, address=$ADDRESS"
echo ""

# Test 2: Get payment details
echo "2. Getting payment details..."
PAYMENT=$(curl -s -X GET "$BASE_URL/api/v2/wallet/payments/?track_id=$TRACK_ID" \
  -H "Authorization: Bearer $TOKEN")

STATUS=$(echo $PAYMENT | jq -r '.results[0].status')
echo "✅ Payment status: $STATUS"
echo ""

# Test 3: Get wallet balance
echo "3. Getting wallet balance..."
WALLET=$(curl -s -X GET "$BASE_URL/api/v2/wallet/wallet/" \
  -H "Authorization: Bearer $TOKEN")

BALANCE=$(echo $WALLET | jq -r '.[0].balance_minor')
echo "✅ Wallet balance: \$$(echo "scale=2; $BALANCE/100" | bc)"
echo ""

echo "✅ All tests completed!"
```

---

## 📊 **7. Test Checklist**

### Frontend Tests
- [ ] Network selection works
- [ ] Only mainnet networks shown
- [ ] Amount validation (min $10)
- [ ] Quick amount buttons work
- [ ] Custom amount input works
- [ ] Payment details display correctly
- [ ] QR code displays
- [ ] Address is copyable
- [ ] Countdown timer works
- [ ] Status check button works
- [ ] Error messages display correctly

### Backend API Tests
- [ ] Create top-up with valid data
- [ ] Reject missing amount_minor
- [ ] Reject missing network_id
- [ ] Reject zero amount
- [ ] Reject negative amount
- [ ] Reject invalid network_id
- [ ] Reject inactive network
- [ ] Require authentication
- [ ] List top-up intents
- [ ] Get payment details

### Webhook Tests
- [ ] HMAC signature validation
- [ ] Reject invalid HMAC
- [ ] Handle "Paying" status
- [ ] Handle "Paid" status (credit wallet)
- [ ] Handle "Failed" status
- [ ] Handle "Expired" status
- [ ] Prevent duplicate crediting
- [ ] Handle missing track_id
- [ ] Handle payment not found
- [ ] Handle invalid JSON

### Edge Cases
- [ ] Duplicate webhook calls
- [ ] Missing track_id
- [ ] Payment not found
- [ ] Invalid JSON
- [ ] Network mismatch
- [ ] Amount mismatch
- [ ] OXA Pay API errors
- [ ] Concurrent top-ups

### Integration Tests
- [ ] Complete flow (create → pay → credit)
- [ ] Multiple concurrent top-ups
- [ ] Wallet balance updates correctly
- [ ] Transaction records created
- [ ] Email notifications sent

---

## 🐛 **8. Debugging Tips**

### Check Logs
```bash
# Backend logs
sudo journalctl -u global-banker -f

# Django logs
tail -f /home/banker/banksite-1/global-banker/logs/*.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Database Queries
```python
# Django shell
python manage.py shell

from wallet.models import TopUpIntent, OxaPayPayment
from accounts.models import User

# Check top-up intents
TopUpIntent.objects.filter(user__email='test@example.com').order_by('-created_at')

# Check payments
OxaPayPayment.objects.filter(track_id='TRACK_ID')

# Check wallet balance
user = User.objects.get(email='test@example.com')
wallet = user.wallet_set.first()
print(f"Balance: ${wallet.balance_minor / 100:.2f}")
```

### Test Webhook Locally
```bash
# Use ngrok to expose local server
ngrok http 8000

# Update OXA Pay callback URL to ngrok URL
# OXA Pay will send webhooks to your local server
```

---

## 📝 **9. Test Data Setup**

### Create Test Networks
```python
# Django shell
from wallet.models import CryptoNetwork

networks = [
    {'name': 'Bitcoin Network', 'native_symbol': 'BTC', 'db_is_testnet': False},
    {'name': 'Ethereum Network', 'native_symbol': 'ETH', 'db_is_testnet': False},
    {'name': 'Tether (USDT)', 'native_symbol': 'USDT', 'db_is_testnet': False},
    # ... etc
]

for net in networks:
    CryptoNetwork.objects.get_or_create(
        native_symbol=net['native_symbol'],
        defaults=net
    )
```

### Create Test User
```python
from accounts.models import User

user = User.objects.create_user(
    username='test@example.com',
    email='test@example.com',
    password='testpass123'
)
```

---

## ✅ **10. Success Criteria**

A successful test should verify:

1. ✅ Top-up creation returns valid payment details
2. ✅ Payment address is valid and unique
3. ✅ Webhook processes correctly with valid HMAC
4. ✅ Wallet is credited when payment confirmed
5. ✅ Transaction record is created
6. ✅ Top-up intent status updates correctly
7. ✅ No duplicate crediting occurs
8. ✅ Error cases are handled gracefully
9. ✅ Frontend displays all information correctly
10. ✅ Email notifications are sent (if configured)

---

## 🔗 **Related Documentation**

- [Server Management Guide](./SERVER_MANAGEMENT_GUIDE.md)
- [OXA Pay Integration](./oxa_pay.md)
- [Webhook Infrastructure](./WEBHOOK_INFRASTRUCTURE_REQUIREMENTS.md)

