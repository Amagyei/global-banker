# OXA Pay Transaction Verification Flow

## Overview
OXA Pay handles blockchain monitoring and transaction verification on their end. Our system receives webhook callbacks when payment status changes, then credits the user's wallet balance.

## Complete Payment Flow

### 1. **User Initiates Payment**
- User creates a top-up intent or checkout via OXA Pay
- Frontend calls `/api/v2/wallet/topups/` or `/api/v2/wallet/invoices/`
- Backend creates `OxaPayPayment` record with status `'pending'`
- OXA Pay API returns payment details (address, QR code, track_id)

### 2. **User Sends Crypto**
- User sends cryptocurrency to the OXA Pay address
- OXA Pay monitors the blockchain for incoming transactions
- **OXA Pay handles all blockchain monitoring** (we don't need to monitor)

### 3. **OXA Pay Detects Transaction**
- OXA Pay detects the transaction on the blockchain
- OXA Pay verifies confirmations (varies by network)
- OXA Pay sends webhook callback to our server

## Webhook Callback Flow

### Webhook Endpoint
- **URL**: `/api/v2/wallet/oxapay/webhook/`
- **Method**: POST
- **Authentication**: HMAC-SHA512 signature verification

### Webhook Payload Structure
```json
{
  "track_id": "151811887",
  "status": "Paying" | "Paid" | "Failed" | "Expired",
  "type": "invoice" | "white_label" | "static_address",
  "amount": 10.0,
  "value": 3.6839,
  "sent_value": 3.6839,
  "currency": "POL",
  "order_id": "ORD-12345",
  "email": "customer@example.com",
  "txs": [{
    "status": "confirming" | "confirmed",
    "tx_hash": "0x...",
    "sent_amount": 10.0,
    "received_amount": 9.85,
    "currency": "POL",
    "network": "Polygon Network",
    "address": "0x...",
    "confirmations": 250,
    "date": 1738494035
  }]
}
```

### Status Progression
1. **"Paying"** - Transaction detected, awaiting confirmations
2. **"Paid"** - Transaction confirmed, ready to credit user
3. **"Failed"** - Transaction failed (insufficient funds, network error, etc.)
4. **"Expired"** - Payment window expired before payment received

## Transaction Verification Process

### Step 1: Signature Verification
```python
# webhooks.py:67-88
hmac_header = request.headers.get('HMAC', '')
calculated_hmac = hmac.new(
    api_key.encode('utf-8'),
    body.encode('utf-8'),
    hashlib.sha512
).hexdigest()

if not hmac.compare_digest(calculated_hmac, hmac_header):
    return HttpResponseBadRequest("Invalid HMAC signature")
```
- Verifies webhook authenticity using HMAC-SHA512
- Uses `OXAPAY_API_KEY` as the secret key
- Prevents fraudulent webhook calls

### Step 2: Find Payment Record
```python
# webhooks.py:114-138
payment = OxaPayPayment.objects.filter(track_id=track_id).first()
```
- Looks up `OxaPayPayment` by `track_id`
- If not found, checks for `OxaPayStaticAddress` and creates payment record

### Step 3: Update Payment Status
```python
# webhooks.py:140-147
payment.status = payment_status  # 'paid', 'failed', 'expired'
if tx_hash:
    payment.tx_hash = tx_hash
payment.raw_response = payload
payment.save()
```
- Updates payment status in database
- Stores transaction hash from `txs` array
- Saves full webhook payload for audit

### Step 4: Process Based on Status

#### Status: "Paid" (Transaction Confirmed)
```python
# webhooks.py:152-154, 177-305
if payment_status == 'paid' and old_status != 'paid':
    process_paid_payment(payment, payload)
```

**What happens:**
1. **Check for duplicate crediting** (prevents double-crediting)
   ```python
   existing_tx = Transaction.objects.filter(
       user=payment.user,
       related_oxapay_payment_id=payment.id,
       direction='credit',
       status='completed'
   ).first()
   if existing_tx:
       return  # Already credited
   ```

2. **Credit user wallet**
   ```python
   wallet, _ = Wallet.objects.get_or_create(
       user=payment.user,
       defaults={'currency_code': 'USD', 'balance_minor': 0}
   )
   amount_minor = int(payment.amount * 100)  # Convert to cents
   wallet.balance_minor += amount_minor
   wallet.save()
   ```

3. **Update top-up intent** (if exists)
   ```python
   if payment.topup_intent:
       payment.topup_intent.status = 'succeeded'
       payment.topup_intent.save()
   ```

4. **Create transaction record**
   ```python
   Transaction.objects.create(
       user=payment.user,
       direction='credit',
       category='topup',
       amount_minor=amount_minor,
       currency_code='USD',
       description=f'Crypto deposit via OXA Pay ({payment.pay_currency.upper()})',
       balance_after_minor=wallet.balance_minor,
       status='completed',
       related_topup_intent_id=payment.topup_intent.id if payment.topup_intent else None,
   )
   ```

5. **Send success notification email**
   ```python
   send_payment_notification(
       user=payment.user,
       payment=payment,
       status='success',
       amount=payment.amount
   )
   ```

#### Status: "Failed"
```python
# webhooks.py:155-157, 308-337
if payment_status == 'failed':
    process_failed_payment(payment, payload)
```
- Updates top-up intent status to `'failed'`
- Sends failure notification email to user

#### Status: "Expired"
```python
# webhooks.py:158-160, 339-367
if payment_status == 'expired':
    process_expired_payment(payment, payload)
```
- Updates top-up intent status to `'expired'`
- Sends expiration notification email to user

#### Status: "Paying"
```python
# webhooks.py:161-163
if payment_status == 'paying':
    logger.info(f"Payment {track_id} is in 'Paying' status, waiting for confirmation")
```
- Just logs the status (waiting for confirmations)
- No wallet credit yet (waiting for "Paid" status)

### Step 5: Return Response
```python
# webhooks.py:166
return HttpResponse("OK", status=200, content_type='text/plain')
```
- **Must return exactly "OK"** (not "ok" or "Ok")
- OXA Pay will retry up to 5 times if response is not "OK"
- Retry schedule: 1 min, 3 min, 30 min, 3 hours

## Order Payment Flow

If payment is linked to an order (`order_id` starts with "ORD-"):

```python
# webhooks.py:193-238
if order_id and order_id.startswith('ORD-'):
    order = Order.objects.get(order_number=order_id, user=payment.user)
    order.status = 'paid'
    order.save()
    
    # Clear cart
    cart.items.all().delete()
    
    # Create transaction record for order payment
    Transaction.objects.create(
        user=payment.user,
        direction='debit',
        category='purchase',
        amount_minor=amount_minor,
        description=f'Order {order.order_number} payment via OXA Pay',
        related_order_id=order.id,
    )
```

## Security Features

### 1. **HMAC Signature Verification**
- Prevents unauthorized webhook calls
- Uses `OXAPAY_API_KEY` as secret key
- HMAC-SHA512 algorithm

### 2. **Duplicate Prevention**
- Checks for existing transaction before crediting
- Uses `related_oxapay_payment_id` to prevent double-crediting
- Atomic database transactions

### 3. **Idempotency**
- Webhook can be called multiple times safely
- Status checks prevent duplicate processing
- Returns "OK" even on errors (to prevent retries)

## Transaction Confirmation Requirements

OXA Pay handles confirmation requirements:
- **Bitcoin**: Typically 1-3 confirmations
- **Ethereum**: Typically 12-30 confirmations
- **Other networks**: Varies by network

OXA Pay only sends "Paid" status when:
- Transaction has sufficient confirmations
- Transaction is confirmed on the blockchain
- Funds are safely received

## Monitoring & Logging

All webhook events are logged:
```python
logger.info(f"OXA Pay webhook: track_id={track_id}, status={payment_status}")
logger.info(f"✅ Credited ${amount_minor/100:.2f} to wallet for user {payment.user.email}")
logger.warning(f"❌ Payment {track_id} failed")
```

## Error Handling

1. **Invalid signature**: Returns 400 Bad Request
2. **Missing track_id**: Returns 400 Bad Request
3. **Payment not found**: Returns 200 OK (prevents retries)
4. **Processing errors**: Logs error, returns 200 OK (prevents retries)

## Summary

**Key Points:**
1. **OXA Pay monitors blockchain** - We don't need to monitor transactions
2. **Webhook callbacks** - OXA Pay sends status updates to our server
3. **Signature verification** - HMAC-SHA512 ensures authenticity
4. **Status-based processing** - Only "Paid" status credits wallet
5. **Duplicate prevention** - Checks prevent double-crediting
6. **Atomic transactions** - Database operations are atomic
7. **Email notifications** - Users are notified of payment status

**Transaction Verification = OXA Pay's Responsibility**
- OXA Pay monitors blockchain
- OXA Pay verifies confirmations
- OXA Pay sends webhook when confirmed
- Our system credits wallet when webhook says "Paid"

