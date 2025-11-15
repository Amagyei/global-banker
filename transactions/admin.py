from django.contrib import admin
from django.utils.html import format_html
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'get_formatted_amount',
        'direction',
        'category',
        'description',
        'status',
        'get_formatted_balance',
        'created_at',
    )
    list_filter = ('direction', 'category', 'status', 'currency_code', 'created_at')
    search_fields = ('user__email', 'description', 'id')
    list_select_related = ('user',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'idempotency_key')
    list_editable = ('status',)  # Allow quick editing of status
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'direction', 'category', 'amount_minor', 'currency_code', 'description', 'status')
        }),
        ('Balance', {
            'fields': ('balance_after_minor',)
        }),
        ('Related Objects', {
            'fields': ('related_order_id', 'related_topup_intent_id', 'related_onchain_tx_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('idempotency_key', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_formatted_amount(self, obj):
        """Format amount with color based on direction"""
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        amount = abs(obj.amount_minor) / 100
        sign = '+' if obj.direction == 'credit' else '-'
        color = 'green' if obj.direction == 'credit' else 'red'
        return format_html(
            '<span style="color: {};">{}{}{:.2f}</span>',
            color,
            sign,
            currency_symbol,
            amount
        )
    get_formatted_amount.short_description = 'Amount'

    def get_formatted_balance(self, obj):
        """Format balance after transaction"""
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        return f"{currency_symbol}{obj.balance_after_minor / 100:.2f}"
    get_formatted_balance.short_description = 'Balance After'
