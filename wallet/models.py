import uuid
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class AddressIndex(models.Model):
    """Atomic counter for address derivation - prevents address reuse"""
    name = models.CharField(max_length=64, unique=True, default='default')
    next_index = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Address Indices"

    def __str__(self):
        return f"{self.name}: {self.next_index}"


class CryptoNetwork(models.Model):
    """Cryptocurrency network configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=20, unique=True)  # "btc", "eth", "tron", "sol"
    name = models.CharField(max_length=100)  # "Bitcoin", "Ethereum", etc.
    chain_id = models.CharField(max_length=50, blank=True)  # For EVM chains
    explorer_url = models.URLField()  # Block explorer base URL
    explorer_api_url = models.URLField()  # Block explorer API URL
    decimals = models.IntegerField()  # 18 for ETH, 8 for BTC
    native_symbol = models.CharField(max_length=10)  # "ETH", "BTC"
    derivation_path = models.CharField(max_length=50, default="m/84'/0'/0'")  # BIP84 for native segwit
    xpub = models.TextField(blank=True)  # Extended public key (encrypted in production)
    is_testnet = models.BooleanField(default=True)  # Use testnet by default
    is_active = models.BooleanField(default=True)
    required_confirmations = models.IntegerField(default=2)  # Confirmations needed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        net = "testnet" if self.effective_is_testnet else "mainnet"
        return f"{self.name} ({net})"
    
    @property
    def effective_is_testnet(self):
        """
        Returns the effective testnet status, respecting WALLET_TEST_MODE.
        If WALLET_TEST_MODE is enabled, always returns True (testnet).
        """
        test_mode = getattr(settings, 'WALLET_TEST_MODE', False)
        if test_mode:
            return True  # Always use testnet in test mode
        return self.is_testnet
    
    @property
    def effective_explorer_api_url(self):
        """
        Returns the effective explorer API URL based on testnet status.
        """
        if self.effective_is_testnet and not self.is_testnet:
            # WALLET_TEST_MODE is forcing testnet, use testnet API
            if 'blockstream' in self.explorer_api_url.lower() and '/testnet' not in self.explorer_api_url.lower():
                return 'https://blockstream.info/testnet/api'
        return self.explorer_api_url
    
    def save(self, *args, **kwargs):
        # Auto-configure testnet based on WALLET_TEST_MODE
        # Note: For OXA Pay, we want to show mainnet networks regardless of WALLET_TEST_MODE
        # WALLET_TEST_MODE only affects the non-custodial wallet system (xpub derivation)
        test_mode = getattr(settings, 'WALLET_TEST_MODE', False)
        
        # Only auto-configure if this is a Bitcoin network and we're using xpub derivation
        # For OXA Pay, we want mainnet networks to remain mainnet
        if test_mode and not self.is_testnet and self.key == 'btc':
            # Only force testnet for Bitcoin if using xpub derivation
            # For other networks or OXA Pay, keep as-is
            pass  # Don't force testnet - allow mainnet for OXA Pay
        
        # Update explorer URLs based on actual is_testnet value
        if self.is_testnet and 'blockstream' in self.explorer_api_url.lower() and '/testnet' not in self.explorer_api_url.lower():
            self.explorer_api_url = 'https://blockstream.info/testnet/api'
            self.explorer_url = 'https://blockstream.info/testnet'
        elif not self.is_testnet and self.key == 'btc' and 'blockstream' in self.explorer_api_url.lower() and '/testnet' in self.explorer_api_url.lower():
            # For mainnet, update URLs if needed
            self.explorer_api_url = 'https://blockstream.info/api'
            self.explorer_url = 'https://blockstream.info'
        super().save(*args, **kwargs)


class Wallet(models.Model):
    """User wallet - tracks balance in USD (one per user)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet', unique=True)
    currency_code = models.CharField(max_length=3, default='USD')
    balance_minor = models.BigIntegerField(default=0)  # Balance in minor units (cents)
    pending_minor = models.BigIntegerField(default=0)  # Pending top-ups
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'currency_code']),
        ]

    def __str__(self):
        return f"{self.user.email} - ${self.balance_minor / 100:.2f}"


class DepositAddress(models.Model):
    """Unique deposit address for user on a network"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposit_addresses')
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='deposit_addresses')
    address = models.CharField(max_length=128, unique=True)
    index = models.BigIntegerField()  # Derivation index
    memo_tag = models.CharField(max_length=100, blank=True)  # For networks that need it (XRP, etc.)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'network', 'is_active']),
            models.Index(fields=['address']),
        ]
        unique_together = [['user', 'network', 'index']]

    def __str__(self):
        return f"{self.user.email} - {self.network.name} - {self.address[:20]}..."


class TopUpIntent(models.Model):
    """Top-up request - tracks user deposit requests for transaction history"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topup_intents')
    amount_minor = models.BigIntegerField()  # Amount in USD minor units (for user history)
    currency_code = models.CharField(max_length=3, default='USD')
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='topup_intents')
    deposit_address = models.ForeignKey(DepositAddress, on_delete=models.CASCADE, related_name='topup_intents', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.amount_minor / 100:.2f} {self.currency_code} - {self.get_status_display()}"


class OnChainTransaction(models.Model):
    """On-chain cryptocurrency transaction"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='onchain_transactions')
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='onchain_transactions')
    tx_hash = models.CharField(max_length=128, unique=True)  # Transaction hash
    from_address = models.CharField(max_length=128)
    to_address = models.CharField(max_length=128)
    amount_atomic = models.BigIntegerField()  # Amount in smallest unit (wei, satoshi)
    amount_minor = models.BigIntegerField()  # Converted to USD minor units
    confirmations = models.IntegerField(default=0)
    required_confirmations = models.IntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    occurred_at = models.DateTimeField()  # When transaction occurred on-chain
    raw = models.JSONField(default=dict, blank=True)  # Raw transaction data
    topup_intent = models.ForeignKey(TopUpIntent, on_delete=models.SET_NULL, null=True, blank=True, related_name='onchain_transactions')
    # sweep_transaction will be added via OneToOneField in SweepTransaction model
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['tx_hash']),
            models.Index(fields=['topup_intent']),
            models.Index(fields=['network', 'status']),
        ]

    def __str__(self):
        return f"{self.network.name} - {self.tx_hash[:20]}... - {self.get_status_display()}"

    def is_confirmed(self):
        return self.confirmations >= self.required_confirmations and self.status == 'confirmed'
    
    # Add sweep_transaction relationship (will be added in migration)
    # sweep_transaction = models.OneToOneField('SweepTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='onchain_tx')


class HotWallet(models.Model):
    """Hot wallet - online wallet that collects deposits from user wallets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='hot_wallets')
    address = models.CharField(max_length=128, unique=True)
    encrypted_xprv = models.TextField()  # AES-256 encrypted extended private key
    derivation_path = models.CharField(max_length=100)  # e.g., "m/84'/1'/1'" for BIP84 testnet hot wallet
    balance_atomic = models.BigIntegerField(default=0)  # Current balance in atomic units
    last_sweep_at = models.DateTimeField(null=True, blank=True)
    last_consolidation_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['network', 'created_at']
        indexes = [
            models.Index(fields=['network', 'is_active']),
            models.Index(fields=['address']),
        ]

    def __str__(self):
        return f"{self.network.name} Hot Wallet - {self.address[:20]}..."


class ColdWallet(models.Model):
    """Cold wallet - offline reserve (only address stored, no private key)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='cold_wallets')
    address = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=100, default='Main Reserve')  # e.g., "Main Reserve", "Backup Reserve"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['network', 'name']
        indexes = [
            models.Index(fields=['network', 'is_active']),
            models.Index(fields=['address']),
        ]

    def __str__(self):
        return f"{self.network.name} Cold Wallet - {self.name}"


class SweepTransaction(models.Model):
    """Tracks sweeps from user deposit addresses to hot wallet"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('broadcast', 'Broadcast'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sweep_transactions')
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='sweep_transactions')
    from_address = models.CharField(max_length=128)  # User deposit address
    to_address = models.CharField(max_length=128)  # Hot wallet address
    amount_atomic = models.BigIntegerField()  # Amount swept in atomic units
    tx_hash = models.CharField(max_length=128, unique=True, null=True, blank=True)
    fee_atomic = models.BigIntegerField(default=0)  # Transaction fee
    confirmations = models.IntegerField(default=0)
    required_confirmations = models.IntegerField(default=1)  # Sweeps need fewer confirmations
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    onchain_tx = models.OneToOneField(OnChainTransaction, on_delete=models.CASCADE, related_name='sweep_transaction')
    hot_wallet = models.ForeignKey(HotWallet, on_delete=models.CASCADE, related_name='sweep_transactions')
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['tx_hash']),
            models.Index(fields=['onchain_tx']),
            models.Index(fields=['network', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Sweep {self.network.name} - {self.from_address[:10]}... → {self.to_address[:10]}... - {self.get_status_display()}"


class ConsolidationTransaction(models.Model):
    """Tracks consolidations from hot wallet to cold wallet"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('broadcast', 'Broadcast'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='consolidation_transactions')
    from_address = models.CharField(max_length=128)  # Hot wallet address
    to_address = models.CharField(max_length=128)  # Cold wallet address
    amount_atomic = models.BigIntegerField()
    tx_hash = models.CharField(max_length=128, unique=True, null=True, blank=True)
    fee_atomic = models.BigIntegerField(default=0)  # Transaction fee
    confirmations = models.IntegerField(default=0)
    required_confirmations = models.IntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    hot_wallet = models.ForeignKey(HotWallet, on_delete=models.CASCADE, related_name='consolidation_transactions')
    cold_wallet = models.ForeignKey(ColdWallet, on_delete=models.CASCADE, related_name='consolidation_transactions')
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['tx_hash']),
            models.Index(fields=['network', 'status']),
            models.Index(fields=['hot_wallet', 'status']),
        ]

    def __str__(self):
        return f"Consolidation {self.network.name} - {self.from_address[:10]}... → {self.to_address[:10]}... - {self.get_status_display()}"


class OxaPayPayment(models.Model):
    """OXA Pay payment record - tracks payments made via OXA Pay gateway"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oxapay_payments')
    topup_intent = models.ForeignKey(TopUpIntent, on_delete=models.CASCADE, related_name='oxapay_payments', null=True, blank=True)
    track_id = models.CharField(max_length=100, unique=True)  # OXA Pay track_id
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='oxapay_payments')
    address = models.CharField(max_length=128)  # OXA Pay generated address
    amount = models.DecimalField(max_digits=20, decimal_places=8)  # Amount in USD
    pay_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)  # Amount in crypto
    pay_currency = models.CharField(max_length=10, default='btc')  # Payment currency (btc, eth, etc.)
    currency = models.CharField(max_length=10, default='usd')  # Invoice currency
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    callback_url = models.URLField(blank=True)
    order_id = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    qr_code = models.URLField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)  # Raw API response
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['track_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['network', 'status']),
        ]

    def __str__(self):
        return f"OXA Pay {self.track_id} - {self.user.email} - {self.get_status_display()}"


class OxaPayStaticAddress(models.Model):
    """OXA Pay static address - reusable addresses for receiving payments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oxapay_static_addresses')
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='oxapay_static_addresses')
    track_id = models.CharField(max_length=100, unique=True)  # OXA Pay track_id
    address = models.CharField(max_length=128, unique=True)  # OXA Pay generated address
    callback_url = models.URLField(blank=True)
    order_id = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    qr_code = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    raw_response = models.JSONField(default=dict, blank=True)  # Raw API response
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'network', 'is_active']),
            models.Index(fields=['track_id']),
            models.Index(fields=['address']),
        ]

    def __str__(self):
        return f"OXA Pay Static {self.address[:20]}... - {self.user.email}"
