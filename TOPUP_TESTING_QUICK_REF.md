# Top-Up Testing Quick Reference

## 🚀 Quick Test Commands

### Run Automated Test Script
```bash
cd /home/banker/banksite-1/global-banker
source ../venv/bin/activate
python test_topup_validation.py
```

### Manual API Tests

#### Create Top-Up
```bash
curl -X POST http://localhost:8000/api/v2/wallet/topups/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_minor": 1000,
    "network_id": "NETWORK_UUID"
  }'
```

#### Get Payment Details
```bash
curl -X GET "http://localhost:8000/api/v2/wallet/payments/?track_id=TRACK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Check Wallet Balance
```bash
curl -X GET http://localhost:8000/api/v2/wallet/wallet/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Test Webhook (Manual)
```bash
curl -X POST http://localhost:8000/api/v2/wallet/webhook/ \
  -H "Content-Type: application/json" \
  -H "HMAC: CALCULATED_HMAC" \
  -d '{
    "track_id": "123456789",
    "status": "Paid",
    "amount": 10.0
  }'
```

---

## 🧪 Test Scenarios

### 1. Happy Path
1. Create top-up → Get track_id and address
2. Send "Paying" webhook → Status updates
3. Send "Paid" webhook → Wallet credited
4. Verify balance increased

### 2. Error Cases
- Missing amount_minor → 400 Bad Request
- Zero amount → 400 Bad Request
- Invalid network → 404 Not Found
- Invalid HMAC → 400 Bad Request (or logged warning)

### 3. Edge Cases
- Duplicate webhook → No double credit
- Expired payment → Status updated, no credit
- Failed payment → Status updated, no credit

---

## 📊 Check Test Results

### Database Queries
```python
python manage.py shell

from wallet.models import TopUpIntent, OxaPayPayment
from accounts.models import User

# Check top-ups
user = User.objects.get(email='test@example.com')
TopUpIntent.objects.filter(user=user).order_by('-created_at')

# Check payments
OxaPayPayment.objects.filter(track_id='TRACK_ID')

# Check wallet
wallet = user.wallet_set.first()
print(f"Balance: ${wallet.balance_minor / 100:.2f}")
```

### View Logs
```bash
# Backend logs
sudo journalctl -u global-banker -f

# Django logs
tail -f logs/*.log
```

---

## ✅ Test Checklist

- [ ] Network selection works
- [ ] Amount validation (min $10)
- [ ] Top-up creation returns payment details
- [ ] Webhook processes correctly
- [ ] Wallet credited on "Paid" status
- [ ] Duplicate prevention works
- [ ] Error cases handled
- [ ] Frontend displays correctly

---

## 📚 Full Documentation

See [TOPUP_VALIDATION_TESTING_GUIDE.md](./TOPUP_VALIDATION_TESTING_GUIDE.md) for complete testing guide.







