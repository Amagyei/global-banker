import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from djmoney.models.fields import MoneyField

User = get_user_model()


class Cart(models.Model):
    """Shopping cart - one per user"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    currency_code = models.CharField(max_length=3, default='USD')  # Always USD for pricing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_minor(self):
        """Calculate total price of all items in cart"""
        from decimal import Decimal
        total = sum((item.total_price_minor.amount for item in self.items.all()), Decimal('0'))
        return total


class CartItem(models.Model):
    """Item in shopping cart - supports both Account and FullzPackage"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey('catalog.Account', on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)
    fullz_package = models.ForeignKey('catalog.FullzPackage', on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    total_price_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ['cart', 'account'],  # prevent duplicate accounts
            ['cart', 'fullz_package'],  # prevent duplicate packages
        ]
        ordering = ['-added_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(account__isnull=False, fullz_package__isnull=True) |
                    models.Q(account__isnull=True, fullz_package__isnull=False)
                ),
                name='cart_item_must_have_account_or_package'
            )
        ]

    def __str__(self):
        item_name = self.account.name if self.account else self.fullz_package.name
        return f"{self.quantity}x {item_name} in {self.cart.user.email}'s cart"

    def save(self, *args, **kwargs):
        """Auto-calculate total_price_minor"""
        self.total_price_minor = self.unit_price_minor.amount * self.quantity
        super().save(*args, **kwargs)


class Order(models.Model):
    """Order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subtotal_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    fees_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', default=0)
    total_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    currency_code = models.CharField(max_length=3, default='USD')  # Always USD for pricing
    recipient = models.JSONField(default=dict)  # recipient details
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.user.email} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Auto-generate order_number if not set"""
        if not self.order_number:
            from django.utils import timezone
            year = timezone.now().year
            count = Order.objects.filter(order_number__startswith=f'ORD-{year}-').count()
            self.order_number = f'ORD-{year}-{count + 1:04d}'
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Item in an order - supports both Account and FullzPackage"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey('catalog.Account', on_delete=models.PROTECT, related_name='order_items', null=True, blank=True)
    fullz_package = models.ForeignKey('catalog.FullzPackage', on_delete=models.PROTECT, related_name='order_items', null=True, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    total_price_minor = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    metadata = models.JSONField(default=dict, blank=True)  # delivery codes, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(account__isnull=False, fullz_package__isnull=True) |
                    models.Q(account__isnull=True, fullz_package__isnull=False)
                ),
                name='order_item_must_have_account_or_package'
            )
        ]

    def __str__(self):
        item_name = self.account.name if self.account else self.fullz_package.name
        return f"{self.quantity}x {item_name} in {self.order.order_number}"

    def save(self, *args, **kwargs):
        """Auto-calculate total_price_minor"""
        self.total_price_minor = self.unit_price_minor.amount * self.quantity
        super().save(*args, **kwargs)


class Fulfillment(models.Model):
    """Order fulfillment tracking"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('issued', 'Issued'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='fulfillments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_payload = models.JSONField(default=dict)  # codes, pins, links, etc.
    delivered_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
        ]

    def __str__(self):
        return f"Fulfillment for {self.order.order_number} - {self.get_status_display()}"
