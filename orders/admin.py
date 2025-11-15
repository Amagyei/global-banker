from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, Order, OrderItem, Fulfillment


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency_code', 'get_total', 'updated_at')
    list_filter = ('currency_code',)
    search_fields = ('user__email',)
    list_select_related = ('user',)

    def get_total(self, obj):
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        return f"{currency_symbol}{obj.total_minor / 100:.2f}"
    get_total.short_description = 'Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('account', 'cart', 'quantity', 'get_total', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('account__name', 'cart__user__email')
    list_select_related = ('account', 'cart', 'cart__user')

    def get_total(self, obj):
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.cart.currency_code, '$')
        return f"{currency_symbol}{obj.total_price_minor / 100:.2f}"
    get_total.short_description = 'Total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'get_total', 'status', 'created_at')
    list_filter = ('status', 'currency_code', 'created_at')
    search_fields = ('order_number', 'user__email')
    list_select_related = ('user',)
    list_editable = ('status',)  # Allow quick editing of status
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Order Details', {
            'fields': ('user', 'order_number', 'status', 'currency_code')
        }),
        ('Totals', {
            'fields': ('subtotal_minor', 'fees_minor', 'total_minor')
        }),
        ('Recipient', {
            'fields': ('recipient',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_total(self, obj):
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        return f"{currency_symbol}{obj.total_minor / 100:.2f}"
    get_total.short_description = 'Total'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'account', 'quantity', 'get_total', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__order_number', 'account__name')
    list_select_related = ('order', 'account')

    def get_total(self, obj):
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.order.currency_code, '$')
        return f"{currency_symbol}{obj.total_price_minor / 100:.2f}"
    get_total.short_description = 'Total'


@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'delivered_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number',)
    list_select_related = ('order',)
    list_editable = ('status',)  # Allow quick editing of status
    readonly_fields = ('created_at', 'updated_at')
