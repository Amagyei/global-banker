# Wallet System Architecture: Current vs Desired

## Overview
This document compares the current wallet implementation with the desired hot/cold wallet architecture, detailing what to add, remove, and modify.

---

## 1. CURRENT SYSTEM ARCHITECTURE

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT SYSTEM                           │
└─────────────────────────────────────────────────────────────┘

User Request
    │
    ▼
┌─────────────────────┐
│  TopUpIntent        │  ← User creates with amount, expiration
│  - amount_minor     │
│  - expires_at       │
│  - status           │
│  - provider_ref     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  DepositAddress     │  ← Generated or reused per user/network
│  - address          │
│  - index            │
│  - user             │
└──────────┬──────────┘
           │
           │ User deposits crypto
           ▼
┌─────────────────────┐
│  BlockchainMonitor  │  ← Polls blockchain for deposits
│  - check_deposit()  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  OnChainTransaction │  ← Records on-chain tx
│  - tx_hash          │
│  - amount_atomic    │
│  - confirmations    │
│  - topup_intent     │  ← Links to TopUpIntent
└──────────┬──────────┘
           │
           │ Amount matching (1% tolerance)
           │ Status: pending → confirmed
           ▼
┌─────────────────────┐
│  Wallet (User)       │  ← Credits user balance
│  - balance_minor     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Transaction        │  ← Records credit in ledger
│  - direction: credit│
│  - category: topup  │
└─────────────────────┘

❌ FUNDS REMAIN IN USER DEPOSIT ADDRESSES
❌ NO SWEEPING MECHANISM
❌ NO HOT/COLD WALLET
```

### Current Models

1. **AddressIndex** ✅ Keep
   - Atomic counter for address derivation
   - Prevents address reuse

2. **CryptoNetwork** ✅ Keep
   - Network configuration (BTC, ETH, etc.)
   - Explorer URLs, decimals, etc.

3. **DepositAddress** ✅ Keep
   - User deposit addresses
   - Derived from master xpub

4. **TopUpIntent** ⚠️ Modify
   - **Keep**: `id`, `user`, `network`, `deposit_address`, `amount_minor`, `status`, `created_at`
   - **Remove**: `expires_at`, `provider_ref`, `'awaiting_confirmations'` status
   - **Purpose**: Transaction history for users

5. **OnChainTransaction** ✅ Keep (minor modifications)
   - Records all on-chain transactions
   - **Modify**: Make `topup_intent` truly optional

6. **Wallet** ✅ Keep
   - User balance tracking (off-chain ledger)

7. **Transaction** ✅ Keep
   - Ledger for all movements

### Current Services

1. **Deposit Address Service** ✅ Keep
   - `create_deposit_address()` - derives addresses from xpub
   - `reserve_next_index()` - atomic index reservation

2. **Blockchain Watcher** ✅ Keep (enhance)
   - `BlockchainMonitor` - monitors deposits
   - `monitor_deposits` command - periodic checking
   - **Enhance**: Trigger sweep after confirmation

3. **Top-Up Intent Service** ⚠️ Simplify
   - `create_topup_intent()` - creates intent
   - **Remove**: TTL/expiration logic
   - **Keep**: Amount tracking for user history

---

## 2. DESIRED SYSTEM ARCHITECTURE

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    DESIRED SYSTEM                            │
└─────────────────────────────────────────────────────────────┘

User Request
    │
    ▼
┌─────────────────────┐
│  TopUpIntent        │  ← User creates with amount (for history)
│  - amount_minor     │
│  - status           │
│  - NO expires_at    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  DepositAddress     │  ← Generated or reused per user/network
│  - address          │
│  - index            │
│  - user             │
└──────────┬──────────┘
           │
           │ User deposits crypto
           ▼
┌─────────────────────┐
│  BlockchainMonitor  │  ← Polls blockchain for deposits
│  - check_deposit()  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  OnChainTransaction │  ← Records on-chain tx
│  - tx_hash          │
│  - amount_atomic    │
│  - confirmations    │
│  - topup_intent     │  ← Optional link
└──────────┬──────────┘
           │
           │ Amount matching (1% tolerance) ✅ KEEP
           │ Status: pending → confirmed
           │ Confirmations >= required
           ▼
┌─────────────────────┐
│  SweepService       │  ← NEW: Sweeps funds to hot wallet
│  - derive_private() │
│  - create_sweep_tx()│
│  - sign_broadcast() │
└──────────┬──────────┘
           │
           │ Sweep transaction
           ▼
┌─────────────────────┐
│  HotWallet          │  ← NEW: Online wallet
│  - address          │
│  - encrypted_xprv   │
│  - balance_atomic   │
└──────────┬──────────┘
           │
           │ Periodic consolidation
           ▼
┌─────────────────────┐
│  HotWalletManager   │  ← NEW: Consolidates to cold
│  - consolidate()    │
└──────────┬──────────┘
           │
           │ Consolidation transaction
           ▼
┌─────────────────────┐
│  ColdWallet         │  ← NEW: Offline reserve
│  - address          │
│  - NO private key   │
└─────────────────────┘

           │
           │ (After sweep confirmation)
           ▼
┌─────────────────────┐
│  Wallet (User)       │  ← Credits user balance
│  - balance_minor     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Transaction        │  ← Records credit + sweep in ledger
│  - direction: credit│
│  - category: topup   │
│  - sweep_tx_hash     │  ← NEW: Link to sweep
└─────────────────────┘
```

### New Models to Add

1. **HotWallet**
```python
class HotWallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    address = models.CharField(max_length=128, unique=True)
    encrypted_xprv = models.TextField()  # AES-256 encrypted
    derivation_path = models.CharField(max_length=100)  # e.g., "m/84'/1'/1'"
    balance_atomic = models.BigIntegerField(default=0)  # Current balance
    last_sweep_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

2. **ColdWallet**
```python
class ColdWallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    address = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=100)  # e.g., "Main Reserve"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

3. **SweepTransaction**
```python
class SweepTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('broadcast', 'Broadcast'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    from_address = models.CharField(max_length=128)  # User deposit address
    to_address = models.CharField(max_length=128)  # Hot wallet address
    amount_atomic = models.BigIntegerField()
    tx_hash = models.CharField(max_length=128, unique=True, null=True)
    fee_atomic = models.BigIntegerField(default=0)
    confirmations = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    onchain_tx = models.OneToOneField(OnChainTransaction, on_delete=models.CASCADE)
    hot_wallet = models.ForeignKey(HotWallet, on_delete=models.CASCADE)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

4. **ConsolidationTransaction**
```python
class ConsolidationTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('broadcast', 'Broadcast'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    from_address = models.CharField(max_length=128)  # Hot wallet
    to_address = models.CharField(max_length=128)  # Cold wallet
    amount_atomic = models.BigIntegerField()
    tx_hash = models.CharField(max_length=128, unique=True, null=True)
    fee_atomic = models.BigIntegerField(default=0)
    confirmations = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    hot_wallet = models.ForeignKey(HotWallet, on_delete=models.CASCADE)
    cold_wallet = models.ForeignKey(ColdWallet, on_delete=models.CASCADE)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### New Services to Add

1. **PrivateKeyManager**
```python
class PrivateKeyManager:
    """Manages encryption/decryption of private keys"""
    
    def encrypt_xprv(self, xprv: str) -> str:
        """Encrypt xprv with AES-256"""
        
    def decrypt_xprv(self, encrypted_xprv: str) -> str:
        """Decrypt xprv"""
        
    def derive_private_key(self, xprv: str, derivation_path: str) -> str:
        """Derive private key from xprv at specific path"""
```

2. **SweepService**
```python
class SweepService:
    """Sweeps funds from user deposit addresses to hot wallet"""
    
    def sweep_deposit(self, onchain_tx: OnChainTransaction) -> SweepTransaction:
        """Sweep funds from user address to hot wallet"""
        # 1. Get deposit address and index
        # 2. Derive private key from master xprv
        # 3. Create sweep transaction
        # 4. Sign transaction
        # 5. Broadcast to blockchain
        # 6. Create SweepTransaction record
        
    def retry_failed_sweep(self, sweep_tx: SweepTransaction):
        """Retry a failed sweep"""
```

3. **HotWalletManager**
```python
class HotWalletManager:
    """Manages hot wallet and consolidates to cold wallet"""
    
    def consolidate_to_cold(self, network: CryptoNetwork, threshold_atomic: int):
        """Consolidate hot wallet to cold when balance exceeds threshold"""
        # 1. Check hot wallet balance
        # 2. If > threshold, create consolidation tx
        # 3. Sign with hot wallet private key
        # 4. Broadcast
        # 5. Create ConsolidationTransaction record
```

### Modified Models

1. **TopUpIntent** - Simplify
```python
# REMOVE:
- expires_at
- provider_ref
- 'awaiting_confirmations' status

# KEEP:
- id, user, network, deposit_address
- amount_minor (for user history)
- status: 'pending', 'succeeded', 'failed'
- created_at, updated_at
```

2. **OnChainTransaction** - Minor changes
```python
# MODIFY:
- topup_intent: Make truly optional (null=True, blank=True)
- Add: sweep_transaction (OneToOneField to SweepTransaction, null=True)
```

3. **Transaction** - Enhance
```python
# ADD:
- sweep_tx_hash (CharField, null=True, blank=True)
- consolidation_tx_hash (CharField, null=True, blank=True)
```

### Enhanced Services

1. **BlockchainMonitor** - Add sweep trigger
```python
def _process_confirmed_transaction(self, onchain_tx):
    """Process confirmed transaction"""
    # 1. Amount matching (KEEP - 1% tolerance)
    # 2. Update TopUpIntent status
    # 3. Trigger sweep to hot wallet
    # 4. After sweep confirmation, credit user wallet
    # 5. Create Transaction record
```

---

## 3. COMPLETE FLOW COMPARISON

### Current Flow

```
1. User creates TopUpIntent (amount, expiration)
2. System generates/reuses DepositAddress
3. User deposits crypto to address
4. BlockchainMonitor detects deposit
5. OnChainTransaction created
6. Amount matched (1% tolerance)
7. After confirmations, credit Wallet
8. Transaction record created
9. ❌ Funds remain in user address
```

### Desired Flow

```
1. User creates TopUpIntent (amount only, for history)
2. System generates/reuses DepositAddress
3. User deposits crypto to address
4. BlockchainMonitor detects deposit
5. OnChainTransaction created
6. Amount matched (1% tolerance) ✅ KEEP
7. After confirmations, SweepService sweeps to HotWallet
8. SweepTransaction created
9. After sweep confirmation, credit Wallet
10. Transaction record created (with sweep_tx_hash)
11. HotWalletManager periodically consolidates to ColdWallet
12. ✅ Funds moved to hot, then cold wallet
```

---

## 4. ADD/REMOVE/MODIFY SUMMARY

### ✅ ADD

**Models:**
- `HotWallet` - Online wallet with encrypted xprv
- `ColdWallet` - Offline reserve (address only)
- `SweepTransaction` - Tracks sweeps from user → hot
- `ConsolidationTransaction` - Tracks hot → cold

**Services:**
- `PrivateKeyManager` - Encrypt/decrypt xprv, derive private keys
- `SweepService` - Sweep funds from user addresses to hot wallet
- `HotWalletManager` - Consolidate hot → cold periodically

**Fields:**
- `Transaction.sweep_tx_hash` - Link to sweep transaction
- `Transaction.consolidation_tx_hash` - Link to consolidation
- `OnChainTransaction.sweep_transaction` - OneToOne to SweepTransaction

**Management Commands:**
- `sweep_deposits` - Sweep confirmed deposits to hot wallet
- `consolidate_hot_wallet` - Consolidate hot → cold
- `retry_failed_sweeps` - Retry failed sweep transactions

**Cron Jobs:**
- Periodic sweep execution (every 5-10 minutes)
- Periodic hot wallet consolidation (daily or when threshold reached)
- Failed sweep retry (every hour)

### ❌ REMOVE

**Fields:**
- `TopUpIntent.expires_at` - No expiration needed
- `TopUpIntent.provider_ref` - Not using payment providers

**Status Choices:**
- `TopUpIntent.'awaiting_confirmations'` - Simplify to pending/succeeded/failed

**Methods:**
- `TopUpIntent.is_expired()` - No expiration logic
- `BlockchainMonitor._simulate_test_deposit()` - Use real testnet

**Logic:**
- TTL/expiration checking in `monitor_deposits`
- Test mode simulation (use real testnet instead)

### ⚠️ MODIFY

**TopUpIntent:**
- Remove expiration/TTL logic
- Keep amount_minor for user history
- Simplify status choices

**OnChainTransaction:**
- Make `topup_intent` truly optional
- Add `sweep_transaction` relationship

**BlockchainMonitor:**
- Add sweep trigger after confirmation
- Keep amount matching logic (1% tolerance)
- Remove test mode simulation

**Transaction:**
- Add sweep/consolidation tx hash fields
- Link to sweep transactions

**create_topup_intent():**
- Remove `ttl_minutes` parameter
- Remove `expires_at` calculation

---

## 5. SECURITY CONSIDERATIONS

### Private Key Management

1. **Master xprv Storage**
   - Encrypt with AES-256 at rest
   - Store in environment variable or encrypted database field
   - Never log or expose in error messages

2. **Hot Wallet xprv**
   - Encrypt with AES-256
   - Store in `HotWallet.encrypted_xprv`
   - Decrypt only when needed for signing
   - Clear from memory after use

3. **Cold Wallet**
   - Never store private key on server
   - Only store address
   - Manual signing for cold wallet transactions (if needed)

### Access Control

- Sweep operations require admin permissions or automated service account
- Hot wallet consolidation requires admin approval or automated threshold
- All private key operations logged and audited

---

## 6. ERROR HANDLING & RETRY

### Sweep Failures

1. **Retry Logic**
   - Automatic retry up to 3 times
   - Exponential backoff (1min, 5min, 15min)
   - Track in `SweepTransaction.retry_count`

2. **Alerting**
   - Email/Slack alert after 3 failed retries
   - Admin dashboard shows failed sweeps
   - Manual retry option in admin

3. **User Experience**
   - User balance not credited until sweep confirmed
   - Show "Processing" status in UI
   - Transaction history shows sweep status

### Consolidation Failures

- Similar retry logic
- Alert if hot wallet balance exceeds threshold for extended period
- Manual consolidation option in admin

---

## 7. MIGRATION PLAN

### Phase 1: Add New Models
1. Create `HotWallet`, `ColdWallet`, `SweepTransaction`, `ConsolidationTransaction` models
2. Run migrations
3. Create initial hot wallet addresses from master xprv
4. Add cold wallet addresses (manual entry)

### Phase 2: Implement Services
1. Implement `PrivateKeyManager`
2. Implement `SweepService`
3. Implement `HotWalletManager`
4. Add management commands

### Phase 3: Integrate with Existing System
1. Modify `BlockchainMonitor` to trigger sweeps
2. Update `_process_confirmed_transaction()` to call sweep
3. Add sweep confirmation tracking
4. Update `Transaction` model with sweep links

### Phase 4: Simplify TopUpIntent
1. Remove `expires_at` field (migration)
2. Remove `provider_ref` field (migration)
3. Remove `'awaiting_confirmations'` status
4. Update `create_topup_intent()` to remove TTL
5. Update `monitor_deposits` to remove expiration logic

### Phase 5: Testing & Deployment
1. Test sweep flow on testnet
2. Test consolidation flow
3. Test retry logic
4. Deploy to production
5. Monitor and adjust

---

## 8. DATABASE SCHEMA CHANGES

### New Tables
- `wallet_hotwallet`
- `wallet_coldwallet`
- `wallet_sweeptransaction`
- `wallet_consolidationtransaction`

### Modified Tables
- `wallet_topupintent` - Remove `expires_at`, `provider_ref`
- `wallet_onchaintransaction` - Add `sweep_transaction_id` (OneToOne)
- `transactions_transaction` - Add `sweep_tx_hash`, `consolidation_tx_hash`

### Indexes
- `wallet_sweeptransaction`: `(status, created_at)`, `(tx_hash)`, `(onchain_tx_id)`
- `wallet_consolidationtransaction`: `(status, created_at)`, `(tx_hash)`

---

This architecture maintains user transaction history (TopUpIntent) while adding the hot/cold wallet infrastructure for secure fund management.

