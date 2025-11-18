# HD Wallet Payment Module Development Manual

## Overview

This manual covers the **Hierarchical Deterministic (HD) Wallet** implementation for the Global Banker platform. The system uses xpub-derived addresses for secure, non-custodial cryptocurrency deposits, with automatic transaction monitoring and balance updates.

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [HD Wallet Principles](#2-hd-wallet-principles)
3. [Django Models](#3-django-models)
4. [Address Derivation](#4-address-derivation)
5. [Transaction Monitoring](#5-transaction-monitoring)
6. [API Integration](#6-api-integration)
7. [Security Considerations](#7-security-considerations)
8. [Testing](#8-testing)

---

## 1. Architecture Overview

### 1.1 System Components

The wallet system consists of:

- **`wallet` Django App**: Core wallet functionality
- **HD Wallet Derivation**: Using `bip_utils` for BIP-32/44/84 address generation
- **Blockchain Monitoring**: Polling-based transaction detection via Blockstream Esplora API
- **Atomic Index Management**: Prevents address reuse through database-level locking
- **USD Balance Tracking**: All balances stored in USD minor units (cents)

### 1.2 Key Features

- ✅ **Non-custodial**: Private keys never stored on server
- ✅ **Deterministic**: Addresses derived from extended public key (xpub)
- ✅ **Atomic Operations**: Prevents address reuse through database transactions
- ✅ **Multi-network Support**: Bitcoin, Ethereum, and other networks via `CryptoNetwork` model
- ✅ **Automatic Monitoring**: Management command for periodic transaction checks
- ✅ **Test Mode**: Mock addresses for development/testing

---

## 2. HD Wallet Principles

### 2.1 Extended Public Key (xpub)

The system uses an **extended public key (xpub)** to derive deposit addresses. This allows:

- Generating unlimited addresses without exposing private keys
- Deterministic address generation (same index = same address)
- Secure server-side operation (private key never touches the server)

**⚠️ CRITICAL SECURITY**: Never store the extended private key (xprv) on the server. Only the xpub is needed for address derivation.

### 2.2 Derivation Path

The system uses **BIP-84** (Native SegWit) for Bitcoin:

```
m/84'/0'/0'/0/{index}
```

- `84'`: Native SegWit (Bech32 addresses starting with `bc1`)
- `0'`: Bitcoin mainnet (or `1'` for testnet)
- `0'`: Account index
- `0`: Change chain (external addresses)
- `{index}`: Address index (incremented atomically)

### 2.3 Address Reuse Prevention

Each user gets **one deposit address per network** that is reused for all top-ups. This:

- Simplifies user experience (one address to remember)
- Reduces blockchain bloat
- Maintains privacy (addresses are still unique per user)

The `DepositAddress` model enforces `unique_together = [['user', 'network', 'index']]` to prevent duplicates.

---

## 3. Django Models

### 3.1 Core Models

#### `AddressIndex`
Atomic counter for address derivation indices. Prevents race conditions when generating addresses.

```python
class AddressIndex(models.Model):
    name = models.CharField(max_length=64, unique=True, default='default')
    next_index = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
```

**Usage**: One index counter per network (e.g., `btc_testnet`, `btc_mainnet`).

#### `CryptoNetwork`
Configuration for each supported cryptocurrency network.

```python
class CryptoNetwork(models.Model):
    key = models.CharField(max_length=20, unique=True)  # "btc", "eth", "tron"
    name = models.CharField(max_length=100)  # "Bitcoin", "Ethereum"
    explorer_api_url = models.URLField()  # Blockstream Esplora API URL
    decimals = models.IntegerField()  # 8 for BTC, 18 for ETH
    native_symbol = models.CharField(max_length=10)  # "BTC", "ETH"
    derivation_path = models.CharField(max_length=50, default="m/84'/0'/0'")
    xpub = models.TextField(blank=True)  # Extended public key
    is_testnet = models.BooleanField(default=True)
    required_confirmations = models.IntegerField(default=2)
```

#### `Wallet`
User wallet tracking balance in USD minor units.

```python
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    currency_code = models.CharField(max_length=3, default='USD')
    balance_minor = models.BigIntegerField(default=0)  # Balance in cents
    pending_minor = models.BigIntegerField(default=0)  # Pending top-ups
```

#### `DepositAddress`
Unique deposit address per user/network combination.

```python
class DepositAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    address = models.CharField(max_length=128, unique=True)
    index = models.BigIntegerField()  # Derivation index
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['user', 'network', 'index']]
```

#### `TopUpIntent`
Represents a user's request to deposit cryptocurrency.

```python
class TopUpIntent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_confirmations', 'Awaiting Confirmations'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount_minor = models.BigIntegerField()  # USD amount in cents
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    deposit_address = models.ForeignKey(DepositAddress, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
```

#### `OnChainTransaction`
Records actual blockchain transactions.

```python
class OnChainTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE)
    tx_hash = models.CharField(max_length=128, unique=True)
    from_address = models.CharField(max_length=128)
    to_address = models.CharField(max_length=128)
    amount_atomic = models.BigIntegerField()  # Satoshis, wei, etc.
    amount_minor = models.BigIntegerField()  # Converted to USD cents
    confirmations = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    topup_intent = models.ForeignKey(TopUpIntent, on_delete=models.SET_NULL, null=True)
```

---

## 4. Address Derivation

### 4.1 Utility Functions (`wallet/utils.py`)

#### Atomic Index Reservation

```python
def reserve_next_index(name="default"):
    """
    Atomically reserve the next address index to prevent address reuse.
    Uses select_for_update to prevent race conditions.
    """
    from .models import AddressIndex
    
    with transaction.atomic():
        obj, _ = AddressIndex.objects.select_for_update().get_or_create(name=name)
        idx = obj.next_index
        obj.next_index = idx + 1
        obj.save()
    return idx
```

**Key Points**:
- Uses `select_for_update()` for database-level locking
- Wrapped in `transaction.atomic()` for consistency
- Prevents two requests from getting the same index

#### Address Derivation

```python
def derive_address_from_xpub(xpub: str, index: int, network_key: str, is_testnet: bool = True):
    """
    Derive a unique address from extended public key (xpub) and index.
    
    Uses bip_utils library for BIP-84 (Native SegWit) derivation.
    Falls back to mock addresses if library unavailable or in test mode.
    """
    if not BIP_UTILS_AVAILABLE:
        # Fallback: Generate mock address for testing
        if network_key.lower() == "btc":
            prefix = "bc1" if is_testnet else "bc1"
            return f"{prefix}{_generate_mock_address(42)}"
        # ... other networks
    
    # Real derivation using bip_utils
    if network_key.lower() == "btc":
        coin = Bip44Coins.BITCOIN_TESTNET if is_testnet else Bip44Coins.BITCOIN
        bip84 = Bip84.FromExtendedKey(xpub, coin)
        addr = bip84.Change(Bip44Changes.CHAIN_EXT).AddressIndex(index).PublicKey().ToAddress()
        return addr
```

**Dependencies**:
- `bip_utils`: Python library for BIP-32/44/49/84 address derivation
- Install: `pip install bip-utils`

#### Creating Deposit Addresses

```python
def create_deposit_address(user, network):
    """
    Create a unique deposit address for a user on a network.
    Uses atomic index reservation to prevent address reuse.
    """
    from wallet.models import DepositAddress
    
    # Reserve next index atomically
    index = reserve_next_index(name=f"{network.key}_{'testnet' if network.is_testnet else 'mainnet'}")
    
    # Derive address from xpub
    xpub = network.xpub or getattr(settings, 'DEFAULT_XPUB', '')
    address = derive_address_from_xpub(xpub, index, network.key, network.is_testnet)
    
    # Create deposit address record
    deposit_address = DepositAddress.objects.create(
        user=user,
        network=network,
        address=address,
        index=index,
        is_active=True
    )
    
    return deposit_address
```

### 4.2 Creating Top-Up Intents

```python
def create_topup_intent(user, amount_minor: int, network, ttl_minutes: int = 30):
    """
    Create a top-up intent with a unique deposit address.
    Reuses existing address if available, otherwise creates new one.
    """
    from wallet.models import TopUpIntent, DepositAddress
    
    # Get or create deposit address for this user/network
    deposit_address = DepositAddress.objects.filter(
        user=user,
        network=network,
        is_active=True
    ).first()
    
    if not deposit_address:
        deposit_address = create_deposit_address(user, network)
    
    # Create top-up intent
    topup = TopUpIntent.objects.create(
        user=user,
        amount_minor=amount_minor,
        currency_code='USD',
        network=network,
        deposit_address=deposit_address,
        status='pending',
        expires_at=timezone.now() + timedelta(minutes=ttl_minutes)
    )
    
    return topup
```

---

## 5. Transaction Monitoring

### 5.1 Blockchain Monitor (`wallet/blockchain.py`)

The `BlockchainMonitor` class handles transaction detection via polling the Blockstream Esplora API.

#### Initialization

```python
class BlockchainMonitor:
    """Monitor blockchain for transactions using Blockstream Esplora API"""
    
    def __init__(self, network):
        self.network = network
        self.base_url = network.explorer_api_url.rstrip('/')
        self.timeout = 10
```

#### Key Methods

**Get Address Transactions**:
```python
def get_address_transactions(self, address):
    """Get all transactions for an address"""
    response = requests.get(
        f"{self.base_url}/address/{address}/txs",
        timeout=self.timeout
    )
    return response.json()
```

**Inspect Transaction**:
```python
def inspect_transaction_for_address(self, txid, address):
    """
    Inspect a transaction and return total sats received by address,
    confirmation status, and block height.
    """
    tx = self.get_transaction(txid)
    # Calculate total received, check confirmation status
    return total_received, confirmed, block_height
```

**Check Deposit Address**:
```python
def check_deposit_address(self, deposit_address, topup_intent=None):
    """
    Check a deposit address for incoming transactions.
    Updates TopUpIntent and creates OnChainTransaction records.
    Credits user wallet when transaction is confirmed.
    """
    # Get transactions for address
    # Process each transaction
    # Create OnChainTransaction records
    # Update TopUpIntent status
    # Credit user wallet if confirmed
    return found_transaction
```

### 5.2 Management Command (`wallet/management/commands/monitor_deposits.py`)

Periodic monitoring via Django management command:

```python
class Command(BaseCommand):
    help = 'Monitor deposit addresses for incoming cryptocurrency transactions'

    def handle(self, *args, **options):
        # Get active networks
        # Get addresses with pending top-ups
        # Check each address using BlockchainMonitor
        # Mark expired top-ups
```

**Usage**:
```bash
# Monitor all networks
python manage.py monitor_deposits

# Monitor specific network
python manage.py monitor_deposits --network btc

# Monitor specific address
python manage.py monitor_deposits --address bc1q...
```

**Cron Setup** (recommended):
```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/project && source venv/bin/activate && python manage.py monitor_deposits
```

### 5.3 Webhook Integration (Future Enhancement)

Currently, the system uses **polling** via the management command. For production, consider implementing **webhooks** for real-time transaction notifications:

**Benefits of Webhooks**:
- Real-time notifications (no polling delay)
- Reduced API calls
- Better scalability

**Implementation Options**:
1. **BlockCypher Webhooks**: Register addresses and receive POST callbacks
2. **Blockstream Esplora Webhooks**: Self-hosted Esplora with webhook support
3. **Custom Webhook Service**: Build your own using blockchain node subscriptions

**Example Webhook Registration** (future):
```python
# wallet/api_integrations.py

def register_webhook(address, network):
    """
    Registers a webhook with BlockCypher for a specific address.
    """
    payload = {
        "event": "unconfirmed-tx",
        "address": address,
        "url": f"{settings.EXTERNAL_HOST}/api/wallet/webhooks/bitcoin_payment/",
        "confirmations": network.required_confirmations,
    }
    
    response = requests.post(
        BLOCKCYPHER_API_URL,
        json=payload,
        params={'token': settings.BLOCKCYPHER_TOKEN},
        timeout=5
    )
    return response.status_code == 201
```

**Webhook View** (future):
```python
# wallet/views.py

@csrf_exempt
@require_http_methods(["POST"])
def bitcoin_payment_webhook(request):
    """
    Receives webhook POST from BlockCypher when transaction detected.
    """
    data = json.loads(request.body)
    address = data.get('address')
    tx_hash = data.get('hash')
    
    # Process transaction
    # Update TopUpIntent
    # Credit wallet
    
    return JsonResponse({'status': 'ok'})
```

---

## 6. API Integration

### 6.1 REST API Endpoints

#### Wallet ViewSet (`wallet/views.py`)

**Get User Wallet**:
```
GET /api/wallet/wallets/
```
Returns the authenticated user's wallet with balance.

#### CryptoNetwork ViewSet

**List Available Networks**:
```
GET /api/wallet/networks/
```
Returns all active cryptocurrency networks.

#### TopUpIntent ViewSet

**Create Top-Up Intent**:
```
POST /api/wallet/topup-intents/
Body: {
    "amount_minor": 2000,  # $20.00 in cents
    "network_id": "uuid-here",
    "ttl_minutes": 30
}
```
Creates a new top-up intent and returns deposit address.

**Check Status**:
```
POST /api/wallet/topup-intents/{id}/check_status/
```
Manually triggers transaction check for a top-up intent.

**List Top-Up Intents**:
```
GET /api/wallet/topup-intents/
```
Returns user's top-up history.

#### OnChainTransaction ViewSet

**List Transactions**:
```
GET /api/wallet/onchain-transactions/
```
Returns user's on-chain transaction history.

### 6.2 Frontend Integration

Example React component for creating top-up:

```typescript
// TopUp.tsx
const createTopUp = async (amount: number, networkId: string) => {
  const response = await api.post('/api/wallet/topup-intents/', {
    amount_minor: amount * 100, // Convert to cents
    network_id: networkId,
    ttl_minutes: 30
  });
  
  const topup = response.data;
  // Display deposit address: topup.deposit_address.address
  // Show QR code, expiration time, etc.
};
```

---

## 7. Security Considerations

### 7.1 Key Management

**✅ DO**:
- Store only the extended public key (xpub) on the server
- Encrypt xpub in production (use Django's `encrypted_fields` or secret manager)
- Use environment variables for sensitive keys
- Rotate keys periodically if compromised

**❌ DON'T**:
- Never store extended private key (xprv) on the server
- Never log private keys or xpub in production
- Never commit keys to version control

### 7.2 Address Generation

**✅ DO**:
- Use atomic index reservation (`select_for_update()`)
- Validate addresses before storing
- Use unique constraints to prevent duplicates

**❌ DON'T**:
- Don't generate addresses without atomic locking
- Don't reuse addresses across users (enforced by unique constraints)

### 7.3 Transaction Verification

**✅ DO**:
- Verify transaction confirmations before crediting wallet
- Check transaction amounts match expected values
- Validate transaction signatures (handled by blockchain)
- Use required confirmation thresholds per network

**❌ DON'T**:
- Don't credit wallet on unconfirmed transactions
- Don't trust client-provided transaction data
- Don't skip confirmation checks

### 7.4 Settings Configuration

```python
# global_banker/settings.py

# Extended public key (xpub) for address derivation
# WARNING: Never store xprv (extended private key) on the server
# In production, encrypt this value and store in secret manager
DEFAULT_XPUB = os.getenv('DEFAULT_XPUB', '')  # Set via environment variable

# Test mode: Use mock addresses instead of real blockchain
WALLET_TEST_MODE = os.getenv('WALLET_TEST_MODE', 'True').lower() == 'true'
```

---

## 8. Testing

### 8.1 Unit Tests

Test address derivation:
```python
def test_reserve_next_index():
    """Test atomic index reservation"""
    idx1 = reserve_next_index()
    idx2 = reserve_next_index()
    assert idx2 == idx1 + 1
```

Test deposit address creation:
```python
def test_create_deposit_address():
    """Test deposit address creation"""
    user = User.objects.create_user('test@example.com')
    network = CryptoNetwork.objects.create(key='btc', ...)
    
    addr = create_deposit_address(user, network)
    assert addr.user == user
    assert addr.network == network
    assert len(addr.address) > 0
```

### 8.2 Integration Tests

Test top-up workflow:
```python
def test_complete_topup_workflow():
    """Test complete top-up workflow"""
    # Create top-up intent
    topup = create_topup_intent(user, 2000, network)
    
    # Simulate transaction detection
    monitor = BlockchainMonitor(network)
    monitor.check_deposit_address(topup.deposit_address, topup)
    
    # Verify wallet credited
    wallet.refresh_from_db()
    assert wallet.balance_minor == 2000
```

### 8.3 Test Mode

When `WALLET_TEST_MODE = True`, the system:
- Generates mock addresses (not real blockchain addresses)
- Skips real API calls to blockchain explorers
- Allows testing without real cryptocurrency

**Enable Test Mode**:
```python
# settings.py
WALLET_TEST_MODE = True  # Development
WALLET_TEST_MODE = False  # Production
```

---

## 9. Operational Notes

### 9.1 Monitoring

**Recommended Monitoring**:
- Run `monitor_deposits` command every 5 minutes via cron
- Monitor command execution logs
- Alert on failed transaction checks
- Track top-up success/failure rates

### 9.2 Database Maintenance

**Index Management**:
- `AddressIndex` counters should never be reset
- Monitor index growth (should be linear with user growth)
- Backup `AddressIndex` regularly

**Transaction Cleanup**:
- Archive old `OnChainTransaction` records (keep for audit)
- Expire old `TopUpIntent` records automatically
- Clean up inactive `DepositAddress` records if needed

### 9.3 Exchange Rate Integration

Currently, the system uses placeholder exchange rates. For production:

1. **Integrate Exchange Rate API**:
   - Use CoinGecko, CoinMarketCap, or similar
   - Cache rates (update every 5-10 minutes)
   - Handle API failures gracefully

2. **Update `BlockchainMonitor.check_deposit_address()`**:
   ```python
   # Convert atomic units to USD
   from wallet.exchange_rates import get_exchange_rate
   rate = get_exchange_rate(network.native_symbol, 'USD')
   amount_minor = int(amount_atomic * rate / (10 ** network.decimals) * 100)
   ```

---

## 10. Summary

This manual provides the foundational architecture for the HD Wallet payment system:

- **Secure Key Management**: xpub-only, never store private keys
- **Deterministic Address Generation**: Using `bip_utils` for BIP-84 derivation
- **Atomic Operations**: Database-level locking prevents address reuse
- **Transaction Monitoring**: Polling-based detection via Blockstream Esplora API
- **Automatic Balance Updates**: Wallet credited when transactions confirmed
- **Multi-network Support**: Bitcoin, Ethereum, and other networks via `CryptoNetwork` model

**Next Steps**:
1. Set up production xpub (encrypted)
2. Configure cron job for `monitor_deposits`
3. Integrate exchange rate API for accurate USD conversion
4. Consider webhook integration for real-time notifications
5. Set up monitoring and alerting for transaction processing

---

## Appendix: Dependencies

```bash
# Required Python packages
pip install bip-utils
pip install requests
pip install django

# Optional: For encrypted xpub storage
pip install django-encrypted-model-fields
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-15  
**Maintained By**: Global Banker Development Team

