# Wallet Monitoring Fix

## Problem Identified

Transactions were stuck in "pending" status since yesterday because the monitoring mechanism had a critical bug:

**The Issue:**
- Line 169 in `blockchain.py` checked if a transaction already existed and **skipped it entirely**
- This meant once a transaction was created, it was **never updated** with new confirmation counts
- Pending transactions would remain pending forever, even after getting enough confirmations on the blockchain

## Solution Implemented

### 1. **Added `_update_pending_transactions()` method**
   - Updates all existing pending transactions for a deposit address
   - Checks blockchain for latest confirmation counts
   - Updates transaction status when enough confirmations are reached
   - Automatically processes confirmed transactions

### 2. **Added `_update_existing_transaction()` method**
   - Updates existing transactions when found in blockchain data
   - Refreshes confirmation counts and status
   - Processes confirmed transactions

### 3. **Added `_process_confirmed_transaction()` method**
   - Centralized logic for processing confirmed transactions
   - Updates top-up intent status
   - Credits user wallet (with duplicate prevention)
   - Creates transaction record
   - Prevents double-crediting by checking if transaction record already exists

### 4. **Refactored `check_deposit_address()`**
   - Now calls `_update_pending_transactions()` at the start
   - Updates existing transactions instead of skipping them
   - Uses centralized `_process_confirmed_transaction()` method

## How It Works Now

1. **Monitoring runs** (via `python manage.py monitor_deposits`)
2. **For each deposit address:**
   - First, updates all existing pending transactions with latest confirmation counts
   - Then, processes new transactions from blockchain
   - Updates existing transactions if found in blockchain data
3. **When transaction gets enough confirmations:**
   - Status changes from "pending" to "confirmed"
   - Top-up intent status changes to "succeeded"
   - User wallet is credited
   - Transaction record is created

## Testing the Fix

To test if pending transactions are now being updated:

```bash
# Run monitoring command
python manage.py monitor_deposits

# Check transaction status
python check_wallet_transactions.py
```

## Next Steps

1. **Run monitoring command** to update existing pending transactions
2. **Set up cron job** to run `monitor_deposits` every 5 minutes:
   ```bash
   */5 * * * * cd /path/to/global_banker && python manage.py monitor_deposits
   ```
3. **Monitor logs** to see transactions being updated

## Expected Behavior

- Pending transactions will now be updated with new confirmation counts
- Transactions will automatically move to "confirmed" when they reach required confirmations
- Wallets will be credited automatically
- No more stuck pending transactions!

