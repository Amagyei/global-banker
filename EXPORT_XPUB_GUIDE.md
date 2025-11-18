# How to Export and Set DEFAULT_XPUB

## Quick Method (Current Shell Session)

### 1. Export the xpub in your current terminal:

```bash
export DEFAULT_XPUB="your-xpub-string-here"
```

**Example:**
```bash
export DEFAULT_XPUB="tpubD6NzVbkrYhZ4WZ..."
```

### 2. Verify it's set:

```bash
echo $DEFAULT_XPUB
```

### 3. Test in Django shell:

```bash
cd /Users/amagyei/dark-web/banksite-1/global_banker
python manage.py shell
```

Then in the shell:
```python
from django.conf import settings
print(settings.DEFAULT_XPUB)
```

---

## Persistent Method (Recommended for Development)

### Option A: Create a `.env` file (if using python-dotenv)

1. Create `.env` file in the project root:
```bash
cd /Users/amagyei/dark-web/banksite-1/global_banker
echo 'DEFAULT_XPUB=your-xpub-string-here' >> .env
```

2. Install python-dotenv (if not already installed):
```bash
pip install python-dotenv
```

3. Load it in `settings.py` (add at the top):
```python
from dotenv import load_dotenv
load_dotenv()
```

### Option B: Add to your shell profile (for local development)

Add to `~/.zshrc` (or `~/.bashrc` if using bash):

```bash
# Add this line to your ~/.zshrc
export DEFAULT_XPUB="your-xpub-string-here"
```

Then reload:
```bash
source ~/.zshrc
```

---

## For Production (Server)

### Method 1: Systemd service file (Recommended)

Edit your Gunicorn systemd service file (e.g., `/etc/systemd/system/global-banker.service`):

```ini
[Service]
Environment="DEFAULT_XPUB=your-xpub-string-here"
Environment="WALLET_TEST_MODE=False"
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart global-banker
```

### Method 2: Environment file

Create `/etc/global-banker/environment`:
```bash
DEFAULT_XPUB=your-xpub-string-here
WALLET_TEST_MODE=False
```

Then reference it in systemd:
```ini
[Service]
EnvironmentFile=/etc/global-banker/environment
```

---

## How to Get Your xpub from a Wallet

### From Electrum (Desktop Wallet):

1. Open Electrum
2. Go to Wallet → Information
3. Look for "Master Public Key" or "xpub"
4. Copy the value (starts with `xpub` for mainnet or `tpub` for testnet)

### From a Hardware Wallet (Ledger/Trezor):

1. Connect your hardware wallet
2. Open the wallet software (Ledger Live, Trezor Suite)
3. Go to your Bitcoin account
4. Look for "Account Public Key" or "Extended Public Key"
5. Export it (usually in Settings → Advanced)

### From Bitcoin Core:

```bash
bitcoin-cli getaddressinfo $(bitcoin-cli getnewaddress) | grep pubkey
```

### Generate a Test xpub (for testing only):

You can use an online tool or generate one programmatically, but **never use a test xpub in production**.

---

## Testing After Export

### 1. Quick test:

```bash
cd /Users/amagyei/dark-web/banksite-1/global_banker
python manage.py shell
```

```python
from django.conf import settings
from wallet.utils import derive_address_from_xpub

xpub = settings.DEFAULT_XPUB
if xpub:
    # Test deriving an address
    address = derive_address_from_xpub(xpub, 0, "btc", is_testnet=True)
    print(f"Test address: {address}")
else:
    print("DEFAULT_XPUB not set!")
```

### 2. Full test:

```bash
python manage.py shell < test_real_address_derivation.py
```

---

## Important Notes

1. **Testnet vs Mainnet:**
   - Testnet xpub starts with `tpub` or `vpub`
   - Mainnet xpub starts with `xpub` or `zpub`
   - Make sure your xpub matches your network setting

2. **Security:**
   - ✅ xpub is safe to store on server (it's public)
   - ❌ Never store xprv (private key) on server
   - 🔒 In production, consider encrypting the xpub

3. **Format:**
   - BIP84 (Native SegWit): Usually starts with `zpub`/`vpub`
   - BIP49 (P2SH SegWit): Usually starts with `ypub`/`upub`
   - BIP44 (Legacy): Usually starts with `xpub`/`tpub`
   - Our system uses BIP84 by default

---

## Troubleshooting

### "DEFAULT_XPUB not set" error:

1. Check if it's exported:
   ```bash
   echo $DEFAULT_XPUB
   ```

2. If empty, export it:
   ```bash
   export DEFAULT_XPUB="your-xpub"
   ```

3. Restart Django shell/server to pick up the change

### "Address derivation error":

1. Check xpub format (should be valid BIP84)
2. Check if xpub matches network (testnet vs mainnet)
3. Try with a known-good testnet xpub first

### "Coin type is not an enumerative of Bip84Coins":

This usually means:
- xpub format is incorrect
- xpub is for a different derivation path
- Try using a BIP84-compatible xpub

