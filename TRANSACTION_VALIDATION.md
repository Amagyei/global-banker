# Transaction Validation System

## Overview

The system validates cryptocurrency deposits through a multi-step process that ensures:
1. **Transaction Detection**: Polling blockchain explorer for new transactions
2. **Amount Verification**: Confirming received amount matches expected amount
3. **Confirmation Requirements**: Waiting for sufficient blockchain confirmations
4. **Exchange Rate Conversion**: Converting crypto to USD at current market rates
5. **Wallet Crediting**: Safely crediting user wallets only after validation

---

## Validation Flow

### Step 1: Transaction Detection

**Method**: Polling-based monitoring (Blockstream Esplora API)

```python
# Runs via: python manage.py monitor_deposits
# Frequency: Every 5 minutes (via cron)

1. Query blockchain explorer for address transactions
2. Get all transactions sent to the deposit address
3. Filter out already-processed transactions (by tx_hash)
```

**Location**: `wallet/blockchain.py` → `check_deposit_address()`

### Step 2: Transaction Inspection

For each new transaction:

```python
1. Extract transaction hash (txid)
2. Get full transaction details from explorer
3. Calculate total amount received by our address
4. Check confirmation status
5. Count current confirmations
```

**Validation Checks**:
- ✅ Transaction exists on blockchain
- ✅ Transaction includes our deposit address as recipient
- ✅ Amount received > 0
- ✅ Transaction not already processed (unique tx_hash)

**Location**: `wallet/blockchain.py` → `inspect_transaction_for_address()`

### Step 3: Amount Verification

**For Top-Up Intents** (when user requested specific amount):

```python
# Expected amount from TopUpIntent
expected_minor = topup_intent.amount_minor  # e.g., 5000 cents = $50.00

# Actual amount received (converted to USD)
actual_minor = convert_crypto_to_usd(
    total_received_atomic,  # e.g., 0.001 BTC
    network.native_symbol,   # "BTC"
    network.decimals         # 8
)

# Validation: Must be within 1% tolerance
tolerance = 0.01  # 1%
if abs(actual_minor - expected_minor) / expected_minor <= tolerance:
    # Amount matches - proceed
else:
    # Amount mismatch - transaction recorded but top-up not completed
```

**Tolerance**: 1% (allows for exchange rate fluctuations)

**Location**: `wallet/blockchain.py` → lines 200-203

### Step 4: Confirmation Requirements

**Confirmation Levels**:

```python
# Network-specific confirmation requirements
Bitcoin Mainnet: 2 confirmations (default, configurable)
Bitcoin Testnet: 1 confirmation
Ethereum: 12 confirmations (typical)

# Status determination
if confirmations >= required_confirmations:
    status = 'confirmed'  # Safe to credit wallet
elif confirmed (in block but < required):
    status = 'pending'     # Wait for more confirmations
else:
    status = 'pending'     # Not yet in block
```

**Why Confirmations Matter**:
- Prevents double-spending attacks
- Ensures transaction is permanently on blockchain
- Reduces risk of chain reorganizations

**Location**: `wallet/blockchain.py` → lines 168-174

### Step 5: Exchange Rate Conversion

**Real-time Rate Fetching**:

```python
# Uses CoinGecko API with 10-second caching
amount_minor = convert_crypto_to_usd(
    total_received_atomic,  # Amount in smallest unit (satoshi, wei)
    network.native_symbol,   # "BTC", "ETH"
    network.decimals         # 8 for BTC, 18 for ETH
)

# Conversion process:
# 1. Get current exchange rate (cached for 10 seconds)
# 2. Convert atomic units to whole units (divide by 10^decimals)
# 3. Multiply by exchange rate
# 4. Convert to minor units (cents) for USD
```

**Caching**: 10 seconds (stays within CoinGecko free tier limits)

**Location**: `wallet/exchange_rates.py` → `convert_crypto_to_usd()`

### Step 6: Wallet Crediting

**Only after all validations pass**:

```python
# Prerequisites:
# ✅ Transaction confirmed (enough confirmations)
# ✅ Amount matches expected (within 1% tolerance)
# ✅ Top-up intent status is 'pending'

# Credit wallet
wallet.balance_minor += amount_minor
wallet.save()

# Update top-up intent
topup_intent.status = 'succeeded'
topup_intent.save()

# Create transaction record
Transaction.objects.create(
    user=user,
    direction='credit',
    category='topup',
    amount_minor=amount_minor,
    currency_code='USD',
    status='completed',
    ...
)
```

**Safety**: Atomic database operations prevent double-crediting

**Location**: `wallet/blockchain.py` → lines 207-229

---

## Security Features

### 1. Duplicate Prevention

```python
# Check if transaction already processed
if OnChainTransaction.objects.filter(tx_hash=txid).exists():
    continue  # Skip - already processed
```

**Prevents**: Double-crediting from same transaction

### 2. Amount Tolerance

```python
# 1% tolerance allows for:
# - Exchange rate fluctuations during confirmation
# - Minor rounding differences
# - Network fee variations

tolerance = 0.01  # 1%
if abs(actual - expected) / expected <= tolerance:
    # Accept
```

**Prevents**: Rejecting valid transactions due to minor rate changes

### 3. Confirmation Requirements

```python
# Network-specific requirements
required_confirmations = network.required_confirmations  # Default: 2

# Only credit after sufficient confirmations
if confirmations >= required_confirmations:
    status = 'confirmed'
    # Safe to credit
```

**Prevents**: Crediting unconfirmed transactions that might be reversed

### 4. Transaction Record Keeping

```python
# Every transaction is recorded
OnChainTransaction.objects.create(
    tx_hash=txid,              # Unique transaction ID
    amount_atomic=...,         # Original crypto amount
    amount_minor=...,          # Converted USD amount
    confirmations=...,         # Current confirmations
    status=...,                # pending/confirmed/failed
    raw=tx_data,               # Full transaction data
    ...
)
```

**Enables**: Audit trail, dispute resolution, debugging

---

## Validation Process Diagram

```
┌─────────────────────────────────────────────────────────┐
│ 1. Monitor Deposit Address (Every 5 minutes)           │
│    - Query Blockstream Esplora API                      │
│    - Get all transactions for address                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Filter New Transactions                              │
│    - Skip if tx_hash already in database                │
│    - Skip if amount received = 0                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Inspect Transaction                                   │
│    - Get full transaction details                        │
│    - Calculate total received by our address             │
│    - Check if confirmed in block                        │
│    - Count confirmations                                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Convert to USD                                       │
│    - Get current exchange rate (CoinGecko, cached)       │
│    - Convert atomic units → whole units                 │
│    - Multiply by exchange rate                           │
│    - Convert to minor units (cents)                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Validate Amount (if TopUpIntent exists)              │
│    - Compare actual vs expected                          │
│    - Check within 1% tolerance                           │
│    - If mismatch: Record but don't credit               │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Check Confirmations                                  │
│    - Compare current vs required                         │
│    - If insufficient: Mark as 'pending'                 │
│    - If sufficient: Mark as 'confirmed'                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Credit Wallet (if all validations pass)              │
│    - Update wallet.balance_minor                        │
│    - Update topup_intent.status = 'succeeded'           │
│    - Create Transaction record                          │
│    - Create OnChainTransaction record                   │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration

### Confirmation Requirements

Set per network in `CryptoNetwork` model:

```python
network.required_confirmations = 2  # Bitcoin mainnet (default)
network.required_confirmations = 1  # Bitcoin testnet
network.required_confirmations = 12 # Ethereum
```

### Amount Tolerance

Currently hardcoded to 1% in `wallet/blockchain.py`:

```python
tolerance = 0.01  # 1%
```

Can be made configurable per network if needed.

### Monitoring Frequency

Set via cron job:

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/project && python manage.py monitor_deposits
```

**Recommendations**:
- **Development**: Every 1-2 minutes (faster testing)
- **Production**: Every 5 minutes (balances speed vs API limits)

---

## Edge Cases Handled

### 1. Partial Payments

**Scenario**: User sends less than expected amount

**Handling**:
- Transaction is recorded in `OnChainTransaction`
- Top-up intent remains `pending`
- User can send additional payment to complete
- Or admin can manually adjust

### 2. Overpayments

**Scenario**: User sends more than expected amount

**Handling**:
- If within 1% tolerance: Full amount credited
- If over tolerance: Transaction recorded, admin review needed

### 3. Multiple Transactions

**Scenario**: User sends multiple transactions to same address

**Handling**:
- Each transaction processed separately
- All amounts accumulated
- Top-up completes when total matches expected

### 4. Chain Reorganizations

**Scenario**: Transaction confirmed then removed from chain

**Handling**:
- Confirmation count decreases
- Status reverts to 'pending'
- Wallet not credited until re-confirmed

### 5. Exchange Rate Fluctuations

**Scenario**: Rate changes between transaction and confirmation

**Handling**:
- Rate used is from time of detection (not transaction time)
- 1% tolerance accounts for minor fluctuations
- Large fluctuations may require manual review

---

## Manual Validation (Admin)

Admins can review and manually approve transactions via Django admin:

1. **View OnChainTransaction**: See all detected transactions
2. **Check Details**: Review raw transaction data
3. **Manual Approval**: Override status if needed
4. **Adjust Amount**: Manually credit wallet if required

**Location**: `wallet/admin.py` → `OnChainTransactionAdmin`

---

## Testing

### Test Mode

When `WALLET_TEST_MODE=True`:
- Simulates deposits automatically
- No real blockchain queries
- Useful for development/testing

### Production Mode

When `WALLET_TEST_MODE=False`:
- Real blockchain queries
- Real exchange rate fetching
- Real wallet crediting

---

## Monitoring & Logging

### Logs

All validation steps are logged:

```python
logger.info(f"Found transaction {txid} for address {address}")
logger.warning(f"Amount mismatch: expected {expected}, got {actual}")
logger.error(f"Failed to process transaction: {error}")
```

### Metrics to Monitor

1. **Transaction Detection Rate**: How many transactions found per run
2. **Confirmation Time**: Average time to reach required confirmations
3. **Amount Mismatches**: Frequency of tolerance violations
4. **API Errors**: Blockstream/CoinGecko API failures
5. **Processing Time**: Time to process each transaction

---

## Future Improvements

### 1. Webhook Support

**Current**: Polling-based (every 5 minutes)
**Future**: Real-time webhooks from blockchain services

**Benefits**:
- Instant detection
- Reduced API calls
- Better user experience

### 2. Multi-Signature Validation

**Current**: Single validation path
**Future**: Multiple independent validators

**Benefits**:
- Increased security
- Redundancy
- Consensus-based validation

### 3. Merkle Proof Verification

**Current**: Trusts blockchain explorer
**Future**: Verify transactions with merkle proofs

**Benefits**:
- Cryptographic proof of inclusion
- Reduced trust in third-party APIs
- Enhanced security

### 4. Transaction Fee Handling

**Current**: Not explicitly tracked
**Future**: Account for network fees in validation

**Benefits**:
- More accurate amount matching
- Better user experience

---

## Summary

The validation system ensures:

✅ **Security**: Multiple checks prevent fraud and errors
✅ **Accuracy**: Amount verification with tolerance
✅ **Reliability**: Confirmation requirements prevent reversals
✅ **Transparency**: Full audit trail of all transactions
✅ **Flexibility**: Handles edge cases gracefully

**Key Validation Points**:
1. Transaction exists on blockchain
2. Amount received matches expected (within tolerance)
3. Sufficient confirmations achieved
4. Exchange rate conversion accurate
5. No duplicate processing

