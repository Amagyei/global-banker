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
        test_mode = getattr(settings, 'WALLET_TEST_MODE', False)
        if test_mode and not self.is_testnet:
            # Force testnet if WALLET_TEST_MODE is enabled
            self.is_testnet = True
            # Update explorer URLs for testnet
            if 'blockstream' in self.explorer_api_url.lower() and '/testnet' not in self.explorer_api_url.lower():
                self.explorer_api_url = 'https://blockstream.info/testnet/api'
                self.explorer_url = 'https://blockstream.info/testnet'
        elif not test_mode and self.is_testnet and self.key == 'btc':
            # For mainnet, update URLs if needed
            if 'blockstream' in self.explorer_api_url.lower() and '/testnet' in self.explorer_api_url.lower():
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
    """Top-up request - user wants to deposit crypto"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_confirmations', 'Awaiting Confirmations'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topup_intents')
    amount_minor = models.BigIntegerField()  # Amount in USD minor units
    currency_code = models.CharField(max_length=3, default='USD')
    network = models.ForeignKey(CryptoNetwork, on_delete=models.CASCADE, related_name='topup_intents')
    deposit_address = models.ForeignKey(DepositAddress, on_delete=models.CASCADE, related_name='topup_intents')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    provider_ref = models.CharField(max_length=200, blank=True)  # External payment reference
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.amount_minor / 100:.2f} {self.currency_code} - {self.get_status_display()}"

    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == 'pending'


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
