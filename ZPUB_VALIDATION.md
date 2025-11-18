# Zpub Validation Issue

## Problem Found

Your `DEFAULT_XPUB` environment variable contains an **invalid character** at position 37.

**Issue:**
- Character at position 37: Cyrillic 'о' (U+043E) 
- This is NOT a valid base58 character
- Base58 only allows: `123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`

**Valid base58 characters:**
- Numbers: 1-9 (excludes 0)
- Uppercase: A-H, J-N, P-Z (excludes I and O)
- Lowercase: a-k, m-z (excludes l)

## Solution

1. **Check your zpub source** - Copy it again from your wallet software
2. **Verify the zpub** - Make sure there are no special characters, spaces, or line breaks
3. **Re-export the zpub** - Use your wallet's export function again

## How to Fix

```bash
# Remove the current (corrupted) xpub
unset DEFAULT_XPUB

# Set it again with the correct zpub (no special characters)
export DEFAULT_XPUB="your-correct-zpub-here"
```

## Verification

A valid zpub should:
- Start with `zpub` (mainnet) or `vpub` (testnet)
- Be exactly 111 characters long
- Contain only base58 characters
- Have no spaces, line breaks, or special characters

## Testing

After fixing, test with:
```python
from wallet.utils import zpub_to_xpub
import os

zpub = os.getenv('DEFAULT_XPUB')
xpub = zpub_to_xpub(zpub)
print(f"Converted: {xpub[:20]}...")
```

