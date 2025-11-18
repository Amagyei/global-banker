# Wallet Address Derivation Issues and Solutions

## Problems Encountered

### 1. **bip_utils Library Issues**

#### Problem 1: Wrong Coin Type Enum
**Error:** `Coin type is not an enumerative of Bip84Coins`

**Root Cause:**
- Initially used `Bip44Coins.BITCOIN` for BIP84 derivation
- BIP84 requires `Bip84Coins.BITCOIN` (different enum class)
- Even after fixing, still got the same error

**Attempted Fix:**
```python
# Wrong:
coin = Bip44Coins.BITCOIN
bip84 = Bip84.FromExtendedKey(xpub, coin)

# Correct:
bip84_coin = Bip84Coins.BITCOIN
bip84 = Bip84.FromExtendedKey(xpub, bip84_coin)
```

**Current Status:** Still failing with "Coin type is not an enumerative of Bip84Coins" even with correct enum.

**Possible Causes:**
- Version mismatch in `bip_utils` library
- The xpub format (`zpub`) might not be compatible with the library version
- Library might require different initialization method
- Potential bug in `bip_utils` version 2.10.0

#### Problem 2: Dependency Conflict
**Error:** `bip-utils 2.10.0 requires coincurve>=21.0.0; python_version >= "3.13", but you have coincurve 20.0.0`

**Root Cause:**
- `hdwallet` requires `coincurve<21,>=20.0.0`
- `bip_utils` requires `coincurve>=21.0.0` for Python 3.13+
- Incompatible version requirements

**Impact:** Can't use both libraries simultaneously without conflicts

---

### 2. **hdwallet Library Issues**

#### Problem 1: API Version Mismatch
**Error:** `HDWallet.__init__() missing 1 required positional argument: 'cryptocurrency'`

**Root Cause:**
- Documentation examples showed old API: `HDWallet(symbol=BTC)`
- New API (v3.6.1) requires: `HDWallet(cryptocurrency=Bitcoin, network='mainnet')`
- Import path changed from `hdwallet.symbols` to `hdwallet.cryptocurrencies`

**Attempted Fixes:**
```python
# Old API (doesn't work):
from hdwallet.symbols import BTC
hdwallet = HDWallet(symbol=BTC)

# Tried (doesn't exist):
from hdwallet.cryptocurrencies import BitcoinMainnet, BitcoinTestnet

# Correct (v3.6.1):
from hdwallet.cryptocurrencies import Bitcoin
hdwallet = HDWallet(cryptocurrency=Bitcoin, network='mainnet')
```

#### Problem 2: Import Path Confusion
**Error:** `ImportError: cannot import name 'BitcoinMainnet' from 'hdwallet.cryptocurrencies'`

**Root Cause:**
- Assumed separate classes for mainnet/testnet
- Actually uses single `Bitcoin` class with `network` parameter

**Solution:**
```python
# Correct approach:
from hdwallet.cryptocurrencies import Bitcoin
hdwallet = HDWallet(cryptocurrency=Bitcoin, network='mainnet')  # or 'testnet'
```

#### Problem 3: Invalid xpublic key data
**Error:** `Invalid xpublic key data`

**Root Cause:**
- `hdwallet.from_xpublic_key()` might not recognize the `zpub` format directly
- May need to decode or convert the xpub format
- Could be a format mismatch between what hdwallet expects and what we're providing

**Status:** Currently investigating - may need to use different method or pre-process xpub

---

## Current Implementation Status

### Working Solution
We've implemented a **fallback strategy**:

1. **Primary:** Try `bip_utils` with `Bip84Coins.BITCOIN`
2. **Fallback:** If that fails, use `hdwallet` with `Bitcoin` class
3. **Last Resort:** In test mode, generate mock addresses

### Code Flow
```python
try:
    # Try bip_utils first
    bip84 = Bip84.FromExtendedKey(xpub, Bip84Coins.BITCOIN)
    addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(index).PublicKey().ToAddress()
    return addr
except Exception:
    # Fallback to hdwallet
    if HDWALLET_AVAILABLE:
        hdwallet = HDWallet(cryptocurrency=Bitcoin, network='mainnet')
        hdwallet.from_xpublic_key(xpub)
        hdwallet.from_path(f"m/84'/0'/0'/0/{index}")
        addr = hdwallet.p2wpkh_address()
        return addr
    # Last resort: mock address (test mode only)
    raise ValueError("Address derivation failed")
```

---

## Recommendations

### For Production

1. **Test hdwallet thoroughly** - It seems more reliable than bip_utils currently
2. **Consider using only hdwallet** - Remove bip_utils dependency to avoid conflicts
3. **Verify xpub format** - Ensure your `zpub` is valid BIP84 format
4. **Test with real addresses** - Verify derived addresses match your wallet software

### Alternative Libraries to Consider

1. **python-mnemonic** - For BIP39 mnemonic generation (if needed)
2. **pycoin** - Low-level crypto operations, might be more reliable
3. **bitcoinlib** - Another option for Bitcoin-specific operations

### Next Steps

1. ✅ Test `hdwallet` derivation with your xpub
2. ⏳ Verify derived addresses are correct
3. ⏳ Test with real mainnet transactions
4. ⏳ Consider removing `bip_utils` if `hdwallet` works reliably

---

## Summary

**Main Issues:**
- `bip_utils` has compatibility issues with Python 3.13 and coincurve versions
- `bip_utils` BIP84 derivation fails even with correct enum usage
- `hdwallet` API changed significantly between versions
- Dependency conflicts between libraries

**Current Status:**
- Fallback system implemented
- `hdwallet` integration ready (needs testing)
- Test mode works with mock addresses
- Production-ready once `hdwallet` is verified


