import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailNotification(models.Model):
    """Track sent email notifications"""
    EMAIL_TYPE_CHOICES = [
        ('welcome', 'Welcome Email'),
        ('order_confirmation', 'Order Confirmation'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('deposit_confirmation', 'Deposit Confirmation'),
        ('order_cancellation', 'Order Cancellation'),
        ('order_delivery', 'Order Delivery'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_notifications')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='email_notifications')
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    sent_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    recipient_email = models.EmailField()
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'sent_at']),
            models.Index(fields=['order', 'email_type']),
        ]
    
    def __str__(self):
        return f"{self.email_type} to {self.recipient_email} - {self.status}"
