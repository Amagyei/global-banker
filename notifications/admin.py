from django.contrib import admin
from .models import EmailNotification


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ('email_type', 'user', 'order', 'status', 'recipient_email', 'sent_at')
    list_filter = ('email_type', 'status', 'sent_at')
    search_fields = ('user__email', 'recipient_email', 'order__order_number')
    list_select_related = ('user', 'order')
    readonly_fields = ('id', 'sent_at')
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'order', 'email_type', 'status', 'recipient_email')
        }),
        ('Metadata', {
            'fields': ('id', 'sent_at', 'error_message'),
            'classes': ('collapse',)
        }),
    )
