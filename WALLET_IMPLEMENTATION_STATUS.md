# Wallet Implementation Status

## Overview
The wallet system is a **non-custodial, xpub-derived cryptocurrency wallet** that allows users to top up their USD balance by sending crypto to unique deposit addresses. The system is currently configured for **Bitcoin testnet** and uses **Blockstream Esplora API** for blockchain monitoring.

## ✅ Implemented Features

### 1. **Core Models**
- **`Wallet`**: User wallet tracking USD balance (one per user)
- **`CryptoNetwork`**: Network configuration (Bitcoin, Ethereum, etc.)
- **`DepositAddress`**: Unique deposit addresses derived from xpub
- **`TopUpIntent`**: Top-up requests with expiration (30 minutes default)
- **`OnChainTransaction`**: On-chain transaction records
- **`AddressIndex`**: Atomic counter for address derivation (prevents reuse)

### 2. **Address Derivation**
- **xpub-based**: Uses extended public key (BIP84 for Bitcoin)
- **Atomic index reservation**: Prevents address reuse via `select_for_update()`
- **Multi-library support**: 
  - Primary: `bip_utils` (BIP84 native SegWit)
  - Fallback: `hdwallet` (BIP32)
  - Fallback: `pycoin` (manual bech32 encoding)
- **Testnet/Mainnet support**: Automatically detects and handles both
- **Depth handling**: Supports depth 1 vpubs (account-level keys)

### 3. **Blockchain Monitoring**
- **Blockstream Esplora API**: Real-time transaction monitoring
- **Automatic detection**: Detects testnet addresses by prefix (`tb1`, `2`, `m`, `n`)
- **Transaction verification**: 
  - Checks confirmations (default: 2)
  - Validates amounts (within 1% tolerance)
  - Creates `OnChainTransaction` records
  - Updates `TopUpIntent` status
  - Credits user wallet balance

### 4. **Exchange Rates**
- **CoinGecko API**: Real-time crypto-to-USD conversion
- **Caching**: 10-second cache (stays within API rate limits)
- **Fallback rates**: Default rates if API fails
- **Supported**: BTC, ETH, USDT, USDC

### 5. **API Endpoints**
- `GET /api/wallet/wallets/` - Get user wallet
- `GET /api/wallet/networks/` - List active crypto networks
- `GET /api/wallet/deposit-addresses/` - List user deposit addresses
- `POST /api/wallet/topups/` - Create top-up intent
- `POST /api/wallet/topups/{id}/check_status/` - Manually check status
- `GET /api/wallet/onchain-transactions/` - List on-chain transactions

### 6. **Frontend Integration**
- **TopUp Page**: Full UI for creating top-ups
- **Wallet Display**: Shows balance in navbar
- **Countdown Timer**: Shows expiration time (MM:SS format)
- **Status Checking**: Manual "Check Payment Status" button
- **QR Code**: Displays deposit address QR code
- **Copy Address**: One-click copy to clipboard

### 7. **Management Commands**
- `python manage.py monitor_deposits` - Monitor deposit addresses (run via cron)
- `python manage.py configure_networks` - Configure networks based on `WALLET_TEST_MODE`

## 🔧 Configuration

### Environment Variables
- **`DEFAULT_XPUB`**: Extended public key (BIP84 vpub for testnet, zpub for mainnet)
- **`WALLET_TEST_MODE`**: Set to `True` for testnet, `False` for mainnet

### Current Status
- **Networks**: 3 configured
- **Wallets**: 10 users have wallets
- **Deposit Addresses**: 9 addresses generated
- **TopUp Intents**: 21 intents created

## ⚠️ Known Limitations

### 1. **Network Support**
- ✅ **Bitcoin (BTC)**: Fully implemented (testnet & mainnet)
- ❌ **Ethereum (ETH)**: Address derivation not implemented (raises `NotImplementedError`)
- ❌ **Other networks**: Not implemented

### 2. **Test Mode**
- Currently in **testnet mode** (`WALLET_TEST_MODE=True`)
- Uses Bitcoin testnet (`vpub` format)
- Explorer: `https://blockstream.info/testnet/api`

### 3. **Transaction Broadcasting**
- System **receives** deposits (monitors blockchain)
- System does **NOT** send/broadcast transactions
- Users must send crypto from external wallets

### 4. **Monitoring**
- Manual monitoring via `monitor_deposits` command
- **Not automated** (requires cron job setup)
- Recommended: Run every 5 minutes

## 🚀 Production Readiness

### ✅ Ready
- Address derivation (atomic, prevents reuse)
- Transaction verification
- Exchange rate conversion
- Frontend integration
- Error handling

### ⚠️ Needs Setup
- **Cron job** for `monitor_deposits` (every 5 minutes)
- **Mainnet xpub** configuration (when ready)
- **Redis cache** for exchange rates (optional, falls back to local memory)
- **HTTPS** for production (required for security)

### ❌ Not Implemented
- Ethereum address derivation
- Multi-signature wallets
- Hot wallet sweeping (for security)
- Transaction fee estimation
- Payment notifications (email/SMS)

## 📝 Usage Flow

1. **User creates top-up**:
   - Selects network (Bitcoin)
   - Enters amount in USD
   - System generates unique deposit address
   - Returns address + QR code

2. **User sends crypto**:
   - Sends BTC to deposit address from external wallet
   - Transaction appears on blockchain

3. **System monitors** (via `monitor_deposits`):
   - Checks deposit address for transactions
   - Verifies amount matches (within 1% tolerance)
   - Waits for confirmations (default: 2)
   - Credits user wallet balance

4. **User sees balance update**:
   - Frontend refreshes wallet balance
   - Transaction appears in history

## 🔒 Security Features

- **Non-custodial**: System never holds private keys
- **Atomic address generation**: Prevents race conditions
- **Amount validation**: 1% tolerance prevents dust attacks
- **Expiration**: Top-ups expire after 30 minutes
- **Status tracking**: Full audit trail via `OnChainTransaction`

## 📊 Current Database State

```
Networks: 3
Wallets: 10
Deposit Addresses: 9
TopUp Intents: 21
```

## 🎯 Next Steps (Optional Enhancements)

1. **Automate monitoring**: Set up cron job for `monitor_deposits`
2. **Ethereum support**: Implement ETH address derivation
3. **Email notifications**: Notify users when deposits are confirmed
4. **Admin dashboard**: View all pending top-ups
5. **Sweeping**: Implement hot wallet for security (advanced)
6. **Multi-currency**: Support other cryptocurrencies

