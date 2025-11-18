# Electrum Export Guide - Getting the Correct vpub

## Problem

You saw the path `m/0h` (or `m/0'`) in Electrum. This is **depth 1**, but we need **depth 3** (account level).

## What `m/0h` Means

- `m` = Master key (depth 0)
- `0h` or `0'` = First hardened derivation (depth 1)
- This is **NOT** the account level we need!

## What We Need

For BIP84 testnet, we need:
- **Path**: `m/84'/1'/0'`
- **Depth**: 3 (account level)
- **Format**: `vpub...` (testnet BIP84)

### Path Breakdown

```
m          = Master key (depth 0)
84'        = BIP84 purpose (depth 1, hardened)
1'         = Testnet coin type (depth 2, hardened)  
0'         = Account 0 (depth 3, hardened) ← WE NEED THIS LEVEL
0          = Change chain (depth 4, not hardened)
index      = Address index (depth 5, not hardened)
```

## How to Find the Correct vpub in Electrum

### Method 1: Wallet Information

1. Open Electrum wallet
2. Go to: **Wallet → Information** (or **Wallet → Master Public Keys**)
3. Look for the **"Master Public Keys"** section
4. You'll see multiple entries - look for:
   - **Path**: `m/84'/1'/0'` (for testnet) or `m/84'/0'/0'` (for mainnet)
   - **Script type**: `p2wpkh` or `Native SegWit`
   - **Format**: `vpub...` (testnet) or `zpub...` (mainnet)
   - **NOT** `m/0h` or `m/0'` (that's the wrong level!)

### Method 2: Check All Master Public Keys

In Electrum's Master Public Keys section, you might see:

```
Standard (p2pkh):     xpub... (path: m/44'/0'/0')
Wrapped SegWit:      ypub... (path: m/49'/0'/0')
Native SegWit:       zpub... (path: m/84'/0'/0')  ← Mainnet
Native SegWit:       vpub... (path: m/84'/1'/0')  ← Testnet ← WE NEED THIS!
```

**For testnet, look for the `vpub` entry with path `m/84'/1'/0'`**

### Method 3: If You Don't See It

If you only see `m/0h` or `m/0'`:

1. **Check wallet type**: Make sure your wallet is:
   - Standard wallet (not multisig)
   - Native SegWit (p2wpkh)
   - Testnet mode enabled

2. **Recreate wallet** (if needed):
   - Create new wallet → Standard wallet → Native SegWit
   - Make sure testnet is enabled
   - Export the master public key

3. **Check Electrum version**: Older versions might not show BIP84 paths correctly

## Verification

Once you have the vpub, test it:

```bash
python check_vpub.py <your_vpub>
```

**Expected output if correct**:
- ✅ Depth: 3
- ✅ Addresses start with `tb1...` (testnet)

**If you see depth 1 or 2**:
- ❌ Still wrong level - keep looking in Electrum

## Quick Checklist

- [ ] Wallet is in **testnet mode**
- [ ] Wallet type is **Standard** (not multisig)
- [ ] Script type is **p2wpkh** (Native SegWit)
- [ ] Path shows **`m/84'/1'/0'`** (3 levels deep)
- [ ] Format is **`vpub...`** (starts with vpub)
- [ ] Test with `check_vpub.py` shows depth 3

## Common Mistakes

❌ **Wrong**: `m/0h` or `m/0'` (depth 1)  
✅ **Correct**: `m/84'/1'/0'` (depth 3)

❌ **Wrong**: `xpub...` or `tpub...` (BIP44/BIP32)  
✅ **Correct**: `vpub...` (BIP84 testnet)

❌ **Wrong**: Mainnet path `m/84'/0'/0'`  
✅ **Correct**: Testnet path `m/84'/1'/0'`

---

**Once you find the vpub at `m/84'/1'/0'`, the system will work!** 🎯

