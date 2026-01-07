# Hot/Cold Wallet Setup Guide

## ⚠️ Important: OXA Pay Handles Everything

**If you're using OXA Pay (which you are), you DON'T need hot/cold wallets!**

OXA Pay automatically:
- ✅ Generates payment addresses for users
- ✅ Collects funds directly to your OXA Pay account
- ✅ Sends webhooks when payments are confirmed
- ✅ Your system credits user wallets automatically

**The hot/cold wallet system is ONLY for the non-custodial wallet system** (xpub derivation), which is NOT used with OXA Pay.

---

## What Are Hot and Cold Wallets? (For Non-Custodial System Only)

### 🔥 Hot Wallet (Online Wallet)
- **Purpose**: Collects deposits from user deposit addresses (xpub-derived addresses)
- **Status**: Online, connected to the internet
- **Security**: Private keys are encrypted and stored on the server
- **Use Case**: Receives funds from user deposits, then consolidates to cold storage
- **Risk Level**: Medium (online = more vulnerable to attacks)
- **When Needed**: Only if using non-custodial wallet system (not OXA Pay)

### ❄️ Cold Wallet (Offline Reserve)
- **Purpose**: Long-term storage of funds
- **Status**: Offline, never connected to the internet
- **Security**: Private keys are NEVER stored on the server (only address stored)
- **Use Case**: Secure reserve where you withdraw funds
- **Risk Level**: Low (offline = much more secure)
- **When Needed**: Only if using non-custodial wallet system (not OXA Pay)

---

## How OXA Pay Works (Your Current Setup)

```
User wants to deposit
         ↓
OXA Pay generates payment address
         ↓
User sends crypto to OXA Pay address
         ↓
OXA Pay collects funds → Goes to YOUR OXA Pay account
         ↓
OXA Pay sends webhook → Your system credits user wallet
         ↓
You withdraw from OXA Pay dashboard/API
```

**No hot/cold wallets needed!** OXA Pay handles all collection.

---

## How Non-Custodial System Works (If You Used It)

```
User deposits crypto → User deposit address (derived from xpub)
         ↓
    (Sweep happens)
         ↓
Hot Wallet (collects deposits)
         ↓
    (Consolidation happens daily)
         ↓
Cold Wallet (secure reserve)
         ↓
You withdraw manually
```

**This is NOT your current setup** - you're using OXA Pay instead.

---

## Do You Need Hot/Cold Wallets?

### ❌ NO - If Using OXA Pay (Your Current Setup)

**You're using OXA Pay, so you DON'T need hot/cold wallets!**

OXA Pay handles everything:
- ✅ Generates payment addresses
- ✅ Collects funds to your OXA Pay account
- ✅ Sends webhooks when payments are confirmed
- ✅ You withdraw directly from OXA Pay dashboard/API

**Skip the setup below** - it's only for non-custodial wallets.

---

### ✅ YES - Only If Using Non-Custodial Wallet System

If you ever want to use the non-custodial wallet system (xpub derivation instead of OXA Pay), then you'll need hot/cold wallets.

---

## Setup Instructions (For Non-Custodial System Only)

### Step 1: Create Hot Wallets

Hot wallets are created manually in Django Admin:

1. Go to Django Admin → Wallet → Hot Wallets
2. Click "Add Hot Wallet"
3. Fill in:
   - **Network**: Select the cryptocurrency network (BTC, ETH, etc.)
   - **Address**: The hot wallet address (generate using your master xprv)
   - **encrypted_xprv**: Encrypted extended private key (use `PrivateKeyManager` to encrypt)
   - **derivation_path**: e.g., `m/84'/0'/1'` for Bitcoin mainnet hot wallet
   - **is_active**: Check this box

**Important**: Hot wallets need private keys to sweep funds from user addresses. These keys must be encrypted using AES-256.

### Step 2: Create Cold Wallets

Cold wallets are simpler - you only store the address:

1. Go to Django Admin → Wallet → Cold Wallets
2. Click "Add Cold Wallet"
3. Fill in:
   - **Network**: Select the cryptocurrency network
   - **Name**: e.g., "Main Reserve", "Backup Reserve"
   - **Address**: The cold wallet address (generate offline using a hardware wallet or paper wallet)
   - **is_active**: Check this box

**CRITICAL**: 
- Never store the private key for cold wallets on the server
- Generate cold wallet addresses offline
- Use hardware wallets (Ledger, Trezor) or paper wallets for cold storage
- Only the address is stored in the database

### Step 3: Configure Consolidation

The system automatically consolidates hot wallet funds to cold storage:
- Runs daily at 2 AM (via Celery Beat)
- Consolidates when hot wallet balance exceeds threshold (default: $1000)
- You can manually trigger consolidation via Django Admin actions

---

## Security Best Practices

### Hot Wallets
✅ **DO:**
- Encrypt private keys with AES-256
- Use strong encryption passwords
- Monitor hot wallet balances regularly
- Set up alerts for large deposits
- Consolidate to cold storage frequently

❌ **DON'T:**
- Store unencrypted private keys
- Keep large amounts in hot wallets
- Share hot wallet private keys
- Use the same key for multiple networks

### Cold Wallets
✅ **DO:**
- Generate addresses offline
- Use hardware wallets (Ledger, Trezor)
- Store private keys in secure physical locations
- Use multi-signature wallets for large amounts
- Regularly verify cold wallet addresses

❌ **DON'T:**
- Store private keys on any server
- Generate cold wallet addresses online
- Share cold wallet addresses publicly
- Use online wallets as cold storage

---

## Withdrawing Funds (For You)

### With OXA Pay (Your Current Setup):
1. **Via OXA Pay Dashboard**: Log into your OXA Pay account and withdraw directly
2. **Via OXA Pay API**: Use their withdrawal API to send funds wherever needed
3. **Simple**: Funds are already in your OXA Pay account - just withdraw!

**No hot/cold wallets needed** - OXA Pay handles everything.

### With Non-Custodial System (If You Used It):
1. **Via Cold Wallet**: Use your cold wallet's private key (stored offline) to send funds
2. **Via Hot Wallet**: Can send from hot wallet, but should consolidate to cold first
3. **Manual Process**: More complex, requires managing private keys securely

**Note**: Since you're using OXA Pay, you don't need this complexity!

---

## Monitoring

### In Django Admin:
- **Hot Wallets**: View balances, last sweep time, consolidation status
- **Cold Wallets**: View addresses and names (balances checked via blockchain explorer)
- **Sweep Transactions**: Monitor all sweeps from user addresses to hot wallets
- **On-Chain Transactions**: See all deposits and their status

### Alerts:
- Large deposits (>$100) trigger alerts to `nakwa234455@gmail.com`
- Failed sweeps trigger alerts
- Reconciliation discrepancies trigger alerts

---

## Example Setup

### Bitcoin Hot Wallet:
```
Network: Bitcoin (mainnet)
Address: bc1q... (generated from master xprv)
Derivation Path: m/84'/0'/1'
Encrypted XPRV: [AES-256 encrypted]
```

### Bitcoin Cold Wallet:
```
Network: Bitcoin (mainnet)
Name: Main Reserve
Address: bc1q... (generated offline, private key stored in hardware wallet)
```

---

## Troubleshooting

### Hot wallet not receiving sweeps?
- Check that `is_active = True`
- Verify the address matches your derivation path
- Check sweep transaction status in admin

### Consolidation not happening?
- Verify cold wallet exists and is active
- Check Celery Beat is running
- Check hot wallet balance exceeds threshold

### Can't see balances?
- Hot wallet balances update automatically after sweeps
- Cold wallet balances need to be checked via blockchain explorer (not stored in DB)

---

## Next Steps

1. **Create hot wallets** for each active network (BTC, ETH, etc.)
2. **Create cold wallets** for each network (generate addresses offline)
3. **Set up Celery workers** to enable automatic sweeps and consolidation
4. **Monitor** via Django Admin and email alerts

For questions or issues, check the reconciliation service or transaction alerts in Django Admin.

