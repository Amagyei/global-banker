# Wallet Balance Update Flow

Complete explanation of how user balances are updated when deposits are successful.

---

## 🔄 **Complete Flow Overview**

```
1. User creates top-up → OXA Pay generates payment address
2. User sends crypto to address → OXA Pay detects payment
3. OXA Pay sends webhook → Backend receives "Paid" status
4. Webhook handler processes payment → Credits user wallet
5. Transaction record created → Balance updated in database
```

---

## 📋 **Step-by-Step Process**

### Step 1: User Creates Top-Up

**Location:** `wallet/views_v2.py` - `TopUpIntentV2ViewSet.create()`

When a user creates a top-up:
1. Frontend calls `/api/v2/wallet/topups/` with `amount_minor` and `network_id`
2. Backend creates a `TopUpIntent` record with status `'pending'`
3. Backend calls OXA Pay API to generate a payment address
4. OXA Pay returns payment details (address, QR code, track_id)
5. Backend creates an `OxaPayPayment` record linked to the top-up
6. Response includes payment address for user to send crypto

**Key Code:**
```python
# wallet/views_v2.py
topup = TopUpIntent.objects.create(
    user=request.user,
    amount_minor=amount_minor,
    currency_code='USD',
    network=network,
    status='pending'  # Initial status
)

# OXA Pay generates payment
oxa_payment = OxaPayPayment.objects.create(
    user=request.user,
    topup_intent=topup,  # Link to top-up
    track_id=oxa_response['track_id'],
    address=oxa_response['address'],
    amount=amount_usd,
    status='pending'
)
```

**At this point:**
- ✅ Top-up intent created (status: `pending`)
- ✅ Payment record created (status: `pending`)
- ❌ Wallet balance NOT updated yet
- ❌ User hasn't sent crypto yet

---

### Step 2: User Sends Crypto

User sends cryptocurrency to the address provided by OXA Pay. This happens outside our system - user uses their own wallet to send funds.

**OXA Pay monitors the blockchain** and detects when payment is received.

---

### Step 3: OXA Pay Sends Webhook

**Location:** `wallet/webhooks.py` - `oxapay_webhook()`

When OXA Pay detects the payment:
1. OXA Pay sends a webhook to `/api/v2/wallet/webhook/`
2. Webhook contains payment status and transaction details
3. Status can be: `"Paying"`, `"Paid"`, `"Failed"`, or `"Expired"`

**Webhook Payload Example:**
```json
{
  "track_id": "123456789",
  "status": "Paid",  // or "Paying", "Failed", "Expired"
  "type": "white_label",
  "amount": 10.0,
  "value": 0.00015,
  "currency": "BTC",
  "txs": [{
    "status": "confirmed",
    "tx_hash": "abc123...",
    "sent_amount": 10.0,
    "received_amount": 9.95,
    "confirmations": 6
  }]
}
```

**Webhook Handler:**
```python
# wallet/webhooks.py
@csrf_exempt
@require_http_methods(["POST"])
def oxapay_webhook(request):
    # 1. Verify HMAC signature
    # 2. Parse payload
    # 3. Find payment record by track_id
    # 4. Update payment status
    # 5. Process based on status
    if payment_status == 'paid':
        process_paid_payment(payment, payload)
```

---

### Step 4: Process Paid Payment

**Location:** `wallet/webhooks.py` - `process_paid_payment()`

This is where the wallet balance gets updated! Here's the exact flow:

#### 4.1 Check for Duplicate Credit

**Prevents double crediting if webhook is called twice:**

```python
# Check if already credited
existing_tx = Transaction.objects.filter(
    user=payment.user,
    related_topup_intent_id=payment.topup_intent.id if payment.topup_intent else None,
    related_oxapay_payment_id=payment.id,
    direction='credit',
    category='topup',
    status='completed'
).first()

if existing_tx:
    logger.info(f"Payment {payment.track_id} already credited, skipping duplicate")
    return  # Exit early - don't credit again
```

#### 4.2 Get or Create User Wallet

```python
# Get or create user wallet
wallet, _ = Wallet.objects.get_or_create(
    user=payment.user,
    defaults={'currency_code': 'USD', 'balance_minor': 0}
)
```

**Note:** If wallet doesn't exist, it's created with `balance_minor=0`.

#### 4.3 Convert Amount to Minor Units

```python
# Convert amount to minor units (cents)
amount_minor = int(payment.amount * 100)
# Example: $10.00 → 1000 cents
```

#### 4.4 **CREDIT THE WALLET** ⭐

**This is the key line that updates the balance:**

```python
# Credit user wallet
wallet.balance_minor += amount_minor
wallet.save()
```

**Example:**
- Before: `wallet.balance_minor = 5000` ($50.00)
- Amount: `amount_minor = 1000` ($10.00)
- After: `wallet.balance_minor = 6000` ($60.00)

#### 4.5 Update Top-Up Intent Status

```python
# Update top-up intent if exists
if payment.topup_intent:
    payment.topup_intent.status = 'succeeded'
    payment.topup_intent.save()
```

#### 4.6 Create Transaction Record

```python
# Create transaction record
Transaction.objects.create(
    user=payment.user,
    direction='credit',  # Money coming in
    category='topup',   # Type of transaction
    amount_minor=amount_minor,
    currency_code='USD',
    description=f'Crypto deposit via OXA Pay ({payment.pay_currency.upper()})',
    balance_after_minor=wallet.balance_minor,  # Balance after this transaction
    status='completed',
    related_topup_intent_id=payment.topup_intent.id if payment.topup_intent else None,
)
```

**Transaction record includes:**
- `amount_minor`: Amount credited (1000 = $10.00)
- `balance_after_minor`: New balance after credit (6000 = $60.00)
- `direction='credit'`: Money added to wallet
- `category='topup'`: Type of transaction
- `status='completed'`: Transaction is complete

#### 4.7 Send Notification Email

```python
# Send success notification email
send_payment_notification(
    user=payment.user,
    payment=payment,
    status='success',
    amount=payment.amount
)
```

---

## 🔒 **Transaction Safety**

The entire process is wrapped in a database transaction:

```python
with db_transaction.atomic():
    # All database operations happen here
    # If any step fails, everything rolls back
    wallet.balance_minor += amount_minor
    wallet.save()
    payment.topup_intent.status = 'succeeded'
    payment.topup_intent.save()
    Transaction.objects.create(...)
```

**Benefits:**
- ✅ All-or-nothing: Either everything succeeds or nothing changes
- ✅ Prevents partial updates (e.g., balance updated but transaction not created)
- ✅ Database consistency guaranteed

---

## 📊 **Complete Code Flow**

Here's the complete code path:

```python
# 1. Webhook received
oxapay_webhook(request)
    ↓
# 2. Parse and validate
payload = json.loads(request.body)
payment = OxaPayPayment.objects.filter(track_id=track_id).first()
    ↓
# 3. Update payment status
payment.status = 'paid'
payment.save()
    ↓
# 4. Process payment
process_paid_payment(payment, payload)
    ↓
# 5. Check for duplicate
existing_tx = Transaction.objects.filter(...).first()
if existing_tx:
    return  # Already credited
    ↓
# 6. Get wallet
wallet, _ = Wallet.objects.get_or_create(user=payment.user, ...)
    ↓
# 7. Calculate amount
amount_minor = int(payment.amount * 100)
    ↓
# 8. UPDATE BALANCE ⭐
wallet.balance_minor += amount_minor
wallet.save()
    ↓
# 9. Update top-up intent
payment.topup_intent.status = 'succeeded'
payment.topup_intent.save()
    ↓
# 10. Create transaction record
Transaction.objects.create(
    direction='credit',
    amount_minor=amount_minor,
    balance_after_minor=wallet.balance_minor,
    ...
)
    ↓
# 11. Send email notification
send_payment_notification(...)
```

---

## 🔍 **Verification Steps**

### Check Wallet Balance
```python
# Django shell
from accounts.models import User
from wallet.models import Wallet

user = User.objects.get(email='user@example.com')
wallet = Wallet.objects.get(user=user)
print(f"Balance: ${wallet.balance_minor / 100:.2f}")
```

### Check Transactions
```python
from transactions.models import Transaction

# Get recent top-up transactions
transactions = Transaction.objects.filter(
    user=user,
    category='topup',
    direction='credit'
).order_by('-created_at')[:10]

for tx in transactions:
    print(f"${tx.amount_minor / 100:.2f} - {tx.description} - Balance: ${tx.balance_after_minor / 100:.2f}")
```

### Check Payment Status
```python
from wallet.models import OxaPayPayment

payment = OxaPayPayment.objects.get(track_id='123456789')
print(f"Status: {payment.status}")
print(f"Amount: ${payment.amount:.2f}")
print(f"Top-up Intent: {payment.topup_intent.status if payment.topup_intent else 'N/A'}")
```

---

## ⚠️ **Important Notes**

### 1. Balance is Updated in Minor Units (Cents)

- **Storage:** `balance_minor` stores balance in cents (e.g., 1000 = $10.00)
- **Display:** Frontend converts to dollars for display
- **Calculation:** `balance_dollars = balance_minor / 100`

### 2. Duplicate Prevention

The system checks for existing transactions before crediting:
- Prevents double crediting if webhook is called twice
- Uses `related_oxapay_payment_id` to track which payment was credited

### 3. Atomic Transactions

All database operations happen in a transaction:
- If any step fails, everything rolls back
- Ensures data consistency

### 4. Status Flow

```
Top-Up Intent: pending → succeeded
Payment:       pending → paying → paid
Wallet:        balance_minor += amount_minor
Transaction:   created with status='completed'
```

### 5. Order Payments vs Top-Ups

The system handles two types of payments:

**Top-Up Payment:**
- Has `topup_intent` linked
- Credits wallet balance
- Creates credit transaction

**Order Payment:**
- Has `order_id` starting with "ORD-"
- Marks order as paid
- Creates debit transaction (money spent)
- Does NOT credit wallet (money is spent, not added)

---

## 🐛 **Troubleshooting**

### Balance Not Updating?

1. **Check webhook logs:**
   ```bash
   sudo journalctl -u global-banker -f | grep webhook
   ```

2. **Check payment status:**
   ```python
   payment = OxaPayPayment.objects.get(track_id='...')
   print(f"Status: {payment.status}")
   ```

3. **Check for errors:**
   ```python
   # Check if transaction was created
   tx = Transaction.objects.filter(
       related_oxapay_payment_id=payment.id,
       direction='credit'
   ).first()
   print(f"Transaction exists: {tx is not None}")
   ```

4. **Check wallet directly:**
   ```python
   wallet = Wallet.objects.get(user=user)
   print(f"Balance: ${wallet.balance_minor / 100:.2f}")
   ```

### Webhook Not Received?

1. **Check webhook endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v2/wallet/webhook/ \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

2. **Check OXA Pay callback URL:**
   - Should be: `https://your-domain.com/api/v2/wallet/webhook/`
   - Must be HTTPS (OXA Pay requires HTTPS)

3. **Check HMAC signature:**
   - Webhook must include valid HMAC header
   - Uses `OXAPAY_API_KEY` as secret

---

## 📚 **Related Files**

- **Webhook Handler:** `wallet/webhooks.py` - `oxapay_webhook()`
- **Payment Processing:** `wallet/webhooks.py` - `process_paid_payment()`
- **Top-Up Creation:** `wallet/views_v2.py` - `TopUpIntentV2ViewSet.create()`
- **Wallet Model:** `wallet/models.py` - `Wallet`
- **Transaction Model:** `transactions/models.py` - `Transaction`

---

## ✅ **Summary**

**When a deposit is successful:**

1. ✅ OXA Pay sends webhook with status `"Paid"`
2. ✅ Webhook handler receives and validates request
3. ✅ Payment record is found by `track_id`
4. ✅ System checks for duplicate credit (prevents double crediting)
5. ✅ **Wallet balance is updated:** `wallet.balance_minor += amount_minor`
6. ✅ Top-up intent status updated to `'succeeded'`
7. ✅ Transaction record created with `direction='credit'`
8. ✅ Email notification sent to user
9. ✅ All operations wrapped in database transaction (atomic)

**The key line that updates the balance:**
```python
wallet.balance_minor += amount_minor
wallet.save()
```

This happens in `wallet/webhooks.py` → `process_paid_payment()` → Line 266.

