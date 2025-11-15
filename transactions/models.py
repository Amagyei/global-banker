import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Transaction(models.Model):
    """Transaction model for all money movements"""
    DIRECTION_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    CATEGORY_CHOICES = [
        ('topup', 'Top Up'),
        ('purchase', 'Purchase'),
        ('transfer', 'Transfer'),
        ('fee', 'Fee'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount_minor = models.BigIntegerField()  # amount in minor units
    currency_code = models.CharField(max_length=3)  # "USD", "GBP", "CAD"
    description = models.CharField(max_length=500)
    balance_after_minor = models.BigIntegerField()  # balance after this transaction
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Related objects (nullable for now - will link when other apps are implemented)
    related_order_id = models.UUIDField(null=True, blank=True)  # Order ID (will be FK later)
    related_topup_intent_id = models.UUIDField(null=True, blank=True)  # TopUpIntent ID (will be FK later)
    related_onchain_tx_id = models.UUIDField(null=True, blank=True)  # OnChainTransaction ID (will be FK later)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'direction']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_direction_display()} {self.get_category_display()} - {self.amount_minor / 100:.2f} {self.currency_code} ({self.get_status_display()})"
