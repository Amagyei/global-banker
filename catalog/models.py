import uuid
import re
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Country(models.Model):
    """Country model for supported countries"""
    code = models.CharField(max_length=3, primary_key=True)  # "US", "UK", "CA"
    name = models.CharField(max_length=100)  # "United States", "United Kingdom", "Canada"
    currency_code = models.CharField(max_length=3)  # "USD", "GBP", "CAD"
    flag_url = models.URLField(blank=True)
    is_supported = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Bank(models.Model):
    """Financial institution - catalog product"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)  # "Chase", "Bank of America", "Wells Fargo", etc.
    logo_url = models.URLField(blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='banks')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['country', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.country.code})"


def generate_sku(bank_name: str, account_id: uuid.UUID) -> str:
    """Generate SKU from bank name and UUID"""
    # Clean bank name: remove special chars, spaces -> uppercase, limit to 10 chars
    clean_name = re.sub(r'[^A-Za-z0-9]', '', bank_name.upper())[:10]
    # Get first 8 chars of UUID (without hyphens)
    uuid_part = str(account_id).replace('-', '')[:8].upper()
    return f"{clean_name}-{uuid_part}"


class Account(models.Model):
    """Bank account product - catalog item"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=100, unique=True, editable=False)  # auto-generated SKU
    name = models.CharField(max_length=200)  # product name
    description = models.TextField()
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name='accounts')
    balance_minor = models.BigIntegerField()  # account balance in minor units (e.g., 77300 for $773.00)
    price_minor = models.BigIntegerField()  # selling price in minor units
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)  # additional product data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bank', 'is_active']),
        ]

    @property
    def country(self):
        """Get country from bank"""
        return self.bank.country

    @property
    def currency_code(self):
        """Get currency code from bank's country"""
        return self.bank.country.currency_code

    def __str__(self):
        return f"{self.name} - {self.bank.name} ({self.sku})"


@receiver(pre_save, sender=Account)
def generate_account_sku(sender, instance, **kwargs):
    """Auto-generate SKU before saving"""
    # Always regenerate SKU to ensure it matches the pattern
    instance.sku = generate_sku(instance.bank.name, instance.id)
