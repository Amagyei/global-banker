# OXA Pay Address Creation Explanation

## How USDT Addresses Are Created

When you create a top-up via OXA Pay, the system uses **white-label payments** to generate addresses. Here's how it works:

### White-Label Payment Flow

1. **Request Creation**: When a user requests a top-up, the system calls OXA Pay's `generate_white_label_payment` API
2. **Address Generation**: OXA Pay generates a **temporary, one-time use address** for that specific payment
3. **Storage**: The address is stored in our database in the `OxaPayPayment` model
4. **Payment Tracking**: Each address is tied to a `track_id` that OXA Pay uses to track the payment

### Why Addresses Don't Show in OXA Pay Dashboard

**White-label payment addresses are temporary and may not appear in your OXA Pay dashboard's static addresses list** because:

1. **One-Time Use**: These addresses are created for a specific payment and expire after the payment lifetime (60 minutes)
2. **Different Endpoint**: White-label payments use `/payment/white-label` endpoint, not `/payment/static-address`
3. **Payment-Specific**: Each address is tied to a specific `track_id` and payment amount

### Static Addresses vs White-Label Payments

| Feature | White-Label Payment | Static Address |
|---------|---------------------|----------------|
| **Endpoint** | `/payment/white-label` | `/payment/static-address` |
| **Address Type** | Temporary, one-time use | Permanent, reusable |
| **Appears in Dashboard** | May not appear | Should appear |
| **Expiration** | Yes (60 minutes default) | No |
| **Use Case** | Single payment | Multiple payments |

### How to See Your Addresses

1. **In Our Database**: All addresses are stored in `OxaPayPayment` model
   - Query: `OxaPayPayment.objects.filter(network__native_symbol='USDT')`
   - Each record has: `track_id`, `address`, `status`, `created_at`

2. **Via OXA Pay API**: You can query payments using the track_id
   - Use OXA Pay's payment status API with the `track_id`

3. **In OXA Pay Dashboard**: 
   - White-label payments may appear in the "Payments" or "Transactions" section
   - They may NOT appear in "Static Addresses" section (that's for static addresses only)

### Current USDT Address Creation

For USDT, the system:
1. Uses `pay_currency='usdt'`
2. Sets `network='TRON'` (USDT on TRON network)
3. Creates a white-label payment (not a static address)
4. Stores the address in `OxaPayPayment` model

### To Create Static Addresses (Permanent)

If you want addresses that appear in your OXA Pay dashboard's static addresses list, you need to:
1. Use the `/api/v2/wallet/oxapay/static-addresses/` endpoint
2. This creates a permanent, reusable address
3. These addresses will appear in your OXA Pay dashboard

### Checking Address Status

You can check if an address is valid by:
1. Looking up the `track_id` in OXA Pay's payment status API
2. Checking the `status` field in our `OxaPayPayment` model
3. Monitoring the webhook callbacks for payment status updates

