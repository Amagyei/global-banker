# OXA Pay API vs. Desired Hot/Cold Wallet Architecture

## Executive Summary

**OXA Pay** is a **custodial payment gateway** that handles wallet management, address generation, and fund sweeping for you. Our desired architecture is a **non-custodial solution** where we control all private keys and manage the hot/cold wallet infrastructure ourselves.

**Verdict**: OXA Pay can **partially solve** the problem but requires **significant architectural changes** and **loses key security benefits** of our non-custodial approach.

---

## OXA Pay API Capabilities

### 1. White Label Payment (`POST /payment/white-label`)
- **Generates payment addresses** on-demand
- **Callback URL** for payment notifications
- **Auto-withdrawal** to specified addresses (can be our cold wallet)
- **Payment tracking** via `track_id`
- **Expiration** (15-2880 minutes)
- **Underpayment tolerance** (0-60%)
- **Multi-currency support**

### 2. Static Address (`POST /payment/static-address`)
- **Generates static addresses** that don't expire
- **Callback URL** for transaction notifications
- **Auto-withdrawal** to specified addresses
- **No expiration** (but revoked after 6 months of inactivity)
- **Trackable** via `track_id`

### 3. Invoice Generation (`POST /payment/invoice`)
- **Payment page URL** generation
- **Expiration** (15-2880 minutes)
- **Redirect URLs** after payment
- **Multi-currency support**

---

## Architecture Comparison

### Our Desired Architecture (Non-Custodial)

```
User → Deposit Address (derived from our xpub)
     → Blockchain Monitor (we poll)
     → Sweep Service (we control private keys)
     → Hot Wallet (our encrypted xprv)
     → Consolidation (we control)
     → Cold Wallet (our address)
```

**Key Characteristics:**
- ✅ **Full control** over private keys
- ✅ **Non-custodial** - funds never leave our control
- ✅ **Customizable** - we control all logic
- ✅ **No third-party fees** (only network fees)
- ❌ **More complex** - we manage everything
- ❌ **More responsibility** - security is on us

### OXA Pay Architecture (Custodial)

```
User → OXA Pay Address (they generate)
     → OXA Pay Monitoring (they handle)
     → OXA Pay Wallet (they control)
     → Auto-withdrawal (they send to our address)
     → Our Cold Wallet (we control)
```

**Key Characteristics:**
- ✅ **Simpler** - they handle monitoring and sweeping
- ✅ **Less code** - no need for sweep service
- ✅ **Reliable** - they handle infrastructure
- ❌ **Custodial** - funds in their wallet temporarily
- ❌ **Third-party dependency** - rely on their service
- ❌ **Fees** - they charge for their service
- ❌ **Less control** - can't customize sweep logic
- ❌ **No hot wallet** - direct to cold wallet only

---

## Feature-by-Feature Comparison

| Feature | Our Architecture | OXA Pay API | Match? |
|---------|-----------------|-------------|--------|
| **Address Generation** | ✅ Derive from master xpub (BIP84) | ✅ They generate addresses | ⚠️ **Different method** |
| **User Deposit Addresses** | ✅ Unique per user/network | ✅ Static addresses available | ✅ **Can work** |
| **Blockchain Monitoring** | ✅ We poll Blockstream API | ✅ They handle monitoring | ✅ **They do it** |
| **Sweep Service** | ✅ We control private keys | ❌ They handle internally | ❌ **No control** |
| **Hot Wallet** | ✅ Our encrypted xprv | ❌ Their wallet (custodial) | ❌ **Not available** |
| **Cold Wallet** | ✅ Our address (offline) | ✅ Auto-withdrawal to our address | ✅ **Can work** |
| **Private Key Control** | ✅ Full control | ❌ They control | ❌ **No control** |
| **Custom Sweep Logic** | ✅ We control timing/fees | ❌ Automatic (no control) | ❌ **No control** |
| **Transaction Fees** | ✅ Only network fees | ❌ Their fees + network fees | ❌ **More expensive** |
| **Callback Notifications** | ✅ We can implement | ✅ Built-in callbacks | ✅ **Available** |
| **Multi-Currency** | ✅ We support multiple | ✅ They support multiple | ✅ **Both support** |
| **Underpayment Tolerance** | ✅ We control (1% in code) | ✅ Configurable (0-60%) | ✅ **Both support** |
| **Expiration** | ❌ We removed (continuous) | ✅ Configurable (15-2880 min) | ⚠️ **Different approach** |

---

## Can OXA Pay Solve Our Problem?

### ✅ What OXA Pay CAN Do

1. **Replace Deposit Address Generation**
   - Use `POST /payment/static-address` to generate addresses per user
   - Addresses don't expire (until 6 months inactivity)
   - Callback URL for payment notifications

2. **Replace Blockchain Monitoring**
   - They monitor addresses automatically
   - Callback notifications when payments arrive
   - No need for our `monitor_deposits` command

3. **Replace Sweep Service (Partially)**
   - Auto-withdrawal sends funds to our cold wallet directly
   - No need for hot wallet (they act as intermediary)
   - No need for our `SweepService`

4. **Cold Wallet Integration**
   - `auto_withdrawal=1` sends directly to our cold wallet address
   - We maintain control of cold wallet (offline)

### ❌ What OXA Pay CANNOT Do

1. **Hot Wallet Architecture**
   - They don't expose a hot wallet concept
   - Funds go: User → OXA Pay Wallet → Our Cold Wallet
   - No intermediate hot wallet for our control

2. **Private Key Control**
   - We never see or control private keys
   - Cannot customize sweep logic, timing, or fees
   - Cannot manually sweep if needed

3. **Custom Sweep Logic**
   - No control over when sweeps happen
   - No control over fee estimation
   - No retry logic customization

4. **Non-Custodial Security**
   - Funds are in their custody temporarily
   - Third-party risk (they could be hacked, go offline, etc.)
  - Regulatory/compliance concerns

---

## Hybrid Approach: OXA Pay + Our Architecture

### Option 1: OXA Pay for User Deposits Only

```
User → OXA Pay Static Address
     → OXA Pay Monitoring (callback)
     → Our Backend (receives callback)
     → Credit User Wallet
     → (No hot/cold wallet - funds stay in OXA Pay)
```

**Pros:**
- ✅ Simpler - no blockchain monitoring needed
- ✅ Reliable - they handle infrastructure
- ✅ Less code - no sweep service needed

**Cons:**
- ❌ Custodial - funds in OXA Pay wallet
- ❌ No hot/cold wallet architecture
- ❌ Third-party dependency
- ❌ Fees

### Option 2: OXA Pay with Auto-Withdrawal to Cold Wallet

```
User → OXA Pay Static Address
     → OXA Pay Monitoring (callback)
     → OXA Pay Auto-Withdrawal (to our cold wallet)
     → Our Backend (receives callback)
     → Credit User Wallet
     → Cold Wallet (we control)
```

**Pros:**
- ✅ Funds go directly to cold wallet
- ✅ No hot wallet needed
- ✅ Simpler than full architecture
- ✅ We control cold wallet

**Cons:**
- ❌ Still custodial (temporary in OXA Pay)
- ❌ No hot wallet for intermediate control
- ❌ Third-party dependency
- ❌ Fees
- ❌ Less control over timing

### Option 3: OXA Pay as Fallback/Alternative

```
Primary: Our Non-Custodial Architecture
Fallback: OXA Pay for users who prefer simpler flow
```

**Pros:**
- ✅ Best of both worlds
- ✅ Users can choose
- ✅ Redundancy

**Cons:**
- ❌ More complex to maintain
- ❌ Two different flows

---

## Detailed Comparison: Our Flow vs. OXA Pay Flow

### Our Desired Flow

```
1. User creates TopUpIntent ($100 USD)
2. System derives DepositAddress from master xpub (m/84'/1'/0'/0/22)
3. User deposits BTC to address
4. BlockchainMonitor detects deposit (polls Blockstream)
5. OnChainTransaction created
6. Amount matched (1% tolerance)
7. SweepService sweeps to HotWallet (we control private key)
8. SweepTransaction created
9. After sweep confirmation, credit User Wallet
10. HotWalletManager consolidates to ColdWallet periodically
11. Transaction record with sweep_tx_hash
```

**Control Points:**
- ✅ We control address generation
- ✅ We control monitoring frequency
- ✅ We control sweep timing
- ✅ We control hot wallet
- ✅ We control consolidation
- ✅ We control all private keys

### OXA Pay Flow

```
1. User creates TopUpIntent ($100 USD)
2. Call OXA Pay API: POST /payment/static-address
   - network: "Bitcoin Network"
   - callback_url: "https://oursite.com/api/webhooks/oxapay"
   - auto_withdrawal: 1
   - (cold wallet address in their settings)
3. OXA Pay returns address and track_id
4. Store track_id with TopUpIntent
5. User deposits BTC to OXA Pay address
6. OXA Pay monitors (we don't need to)
7. OXA Pay sends callback to our webhook
8. We verify callback signature
9. Credit User Wallet
10. OXA Pay auto-withdraws to our cold wallet (we don't control timing)
11. Transaction record (no sweep_tx_hash - handled by OXA Pay)
```

**Control Points:**
- ❌ They control address generation
- ✅ They handle monitoring (we get callbacks)
- ❌ They control sweep timing (automatic)
- ❌ No hot wallet (direct to cold)
- ❌ They control consolidation (automatic)
- ❌ We don't control private keys

---

## Cost Comparison

### Our Architecture
- **Infrastructure**: Server costs (already have)
- **Blockchain Fees**: Network fees only (minimal)
- **Development**: One-time (already done)
- **Maintenance**: Ongoing monitoring/updates
- **Total**: ~$0/month (just server costs)

### OXA Pay
- **API Fees**: Per transaction fee (typically 0.5-2%)
- **Infrastructure**: Included in fees
- **Development**: Integration work
- **Maintenance**: Minimal (they handle it)
- **Total**: ~0.5-2% of all transactions

**Example**: $10,000/month in deposits
- Our architecture: $0 fees
- OXA Pay: $50-200/month in fees

---

## Security Comparison

### Our Architecture
- ✅ **Non-custodial**: Funds never leave our control
- ✅ **Private keys**: Encrypted, under our control
- ✅ **Hot wallet**: Minimal funds, auto-swept
- ✅ **Cold wallet**: Offline, maximum security
- ⚠️ **Our responsibility**: We handle all security
- ⚠️ **Complexity**: More attack surface

### OXA Pay
- ⚠️ **Custodial**: Funds temporarily in their wallet
- ❌ **Private keys**: They control (we never see)
- ⚠️ **Third-party risk**: They could be hacked
- ✅ **Cold wallet**: We control (offline)
- ✅ **Less complexity**: They handle security
- ⚠️ **Dependency**: If they go down, we're affected

---

## Recommendation

### Use OXA Pay IF:
1. ✅ You want **simpler implementation** (less code)
2. ✅ You're **okay with custodial** solution (temporary)
3. ✅ You want **reliable infrastructure** (they handle it)
4. ✅ You're **okay with fees** (0.5-2% per transaction)
5. ✅ You **don't need hot wallet** (direct to cold is fine)
6. ✅ You **don't need custom sweep logic**

### Keep Our Architecture IF:
1. ✅ You want **non-custodial** solution (full control)
2. ✅ You want **no third-party fees** (only network fees)
3. ✅ You need **hot wallet** for intermediate control
4. ✅ You need **custom sweep logic** (timing, fees, retries)
5. ✅ You want **full private key control**
6. ✅ You're **okay with more complexity** (we manage it)

---

## Hybrid Recommendation

**Best of Both Worlds:**

1. **Primary**: Use our non-custodial architecture (already implemented)
2. **Alternative**: Offer OXA Pay as an option for users who want simpler flow
3. **Migration Path**: Start with our architecture, add OXA Pay later if needed

**Implementation Strategy:**
- Keep current architecture as primary
- Add OXA Pay integration as alternative payment method
- Users can choose: "Direct Crypto" (our system) or "OXA Pay" (simpler)
- Both credit the same user wallet

---

## Conclusion

**OXA Pay can partially solve the problem** but requires **significant architectural changes** and **loses key benefits**:

1. ❌ **No hot wallet** - they handle sweeping internally
2. ❌ **Custodial** - funds temporarily in their control
3. ❌ **Fees** - 0.5-2% per transaction
4. ❌ **Less control** - can't customize sweep logic
5. ✅ **Simpler** - less code to maintain
6. ✅ **Reliable** - they handle infrastructure

**Our current implementation is better suited** for a non-custodial, full-control architecture. OXA Pay would be a **step backward** in terms of control and security, though it would be **simpler to maintain**.

**Recommendation**: **Keep our architecture** as primary. Consider OXA Pay only if:
- You need a simpler solution quickly
- You're okay with custodial approach
- Fees are acceptable
- You don't need hot wallet functionality

