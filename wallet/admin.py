from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AddressIndex,
    CryptoNetwork,
    Wallet,
    DepositAddress,
    TopUpIntent,
    OnChainTransaction,
    OxaPayPayment,
    OxaPayStaticAddress,
)


@admin.register(AddressIndex)
class AddressIndexAdmin(admin.ModelAdmin):
    list_display = ('name', 'next_index', 'updated_at')
    readonly_fields = ('next_index', 'updated_at')


@admin.register(CryptoNetwork)
class CryptoNetworkAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'native_symbol', 'is_testnet', 'is_active', 'required_confirmations')
    list_filter = ('is_testnet', 'is_active')
    search_fields = ('name', 'key', 'native_symbol')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Network Info', {
            'fields': ('name', 'key', 'native_symbol', 'chain_id')
        }),
        ('Configuration', {
            'fields': ('decimals', 'derivation_path', 'required_confirmations')
        }),
        ('Block Explorer', {
            'fields': ('explorer_url', 'explorer_api_url')
        }),
        ('Keys', {
            'fields': ('xpub', 'is_testnet'),
            'description': 'WARNING: xpub should be encrypted in production. Never store xprv on server.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_balance', 'get_pending', 'updated_at')
    list_filter = ('currency_code', 'updated_at')
    search_fields = ('user__email',)
    list_select_related = ('user',)
    readonly_fields = ('id', 'updated_at')

    def get_balance(self, obj):
        return f"${obj.balance_minor / 100:.2f}"
    get_balance.short_description = 'Balance'

    def get_pending(self, obj):
        return f"${obj.pending_minor / 100:.2f}"
    get_pending.short_description = 'Pending'


@admin.register(DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'network', 'address_short', 'index', 'is_active', 'created_at')
    list_filter = ('network', 'is_active', 'created_at')
    search_fields = ('user__email', 'address')
    list_select_related = ('user', 'network')
    readonly_fields = ('id', 'created_at')

    def address_short(self, obj):
        return f"{obj.address[:20]}...{obj.address[-10:]}"
    address_short.short_description = 'Address'


@admin.register(TopUpIntent)
class TopUpIntentAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_amount', 'network', 'status', 'created_at')
    list_filter = ('status', 'network', 'created_at')
    search_fields = ('user__email', 'deposit_address__address')
    list_select_related = ('user', 'network', 'deposit_address')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_editable = ('status',)  # Allow quick status updates

    fieldsets = (
        ('Top-Up Details', {
            'fields': ('user', 'amount_minor', 'currency_code', 'network', 'status')
        }),
        ('Deposit Address', {
            'fields': ('deposit_address',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_amount(self, obj):
        return f"${obj.amount_minor / 100:.2f}"
    get_amount.short_description = 'Amount'


@admin.register(OnChainTransaction)
class OnChainTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'tx_hash_short',
        'user',
        'network',
        'get_amount_crypto',
        'get_amount_usd',
        'confirmations',
        'status',
        'occurred_at',
    )
    list_filter = ('network', 'status', 'occurred_at')
    search_fields = ('tx_hash', 'user__email', 'from_address', 'to_address')
    list_select_related = ('user', 'network', 'topup_intent')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'occurred_at'

    fieldsets = (
        ('Transaction Details', {
            'fields': ('tx_hash', 'network', 'user', 'status')
        }),
        ('Addresses', {
            'fields': ('from_address', 'to_address')
        }),
        ('Amounts', {
            'fields': ('amount_atomic', 'amount_minor', 'confirmations', 'required_confirmations')
        }),
        ('Timing', {
            'fields': ('occurred_at',)
        }),
        ('Relations', {
            'fields': ('topup_intent',),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('raw',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def tx_hash_short(self, obj):
        return f"{obj.tx_hash[:16]}...{obj.tx_hash[-8:]}"
    tx_hash_short.short_description = 'TX Hash'

    def get_amount_crypto(self, obj):
        decimals = obj.network.decimals
        amount = obj.amount_atomic / (10 ** decimals)
        return f"{amount:.{min(decimals, 8)}f} {obj.network.native_symbol}"
    get_amount_crypto.short_description = 'Amount (Crypto)'

    def get_amount_usd(self, obj):
        return f"${obj.amount_minor / 100:.2f}"
    get_amount_usd.short_description = 'Amount (USD)'


@admin.register(OxaPayPayment)
class OxaPayPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'track_id_short',
        'user',
        'network',
        'get_amount_display',
        'status',
        'created_at',
    )
    list_filter = ('status', 'network', 'pay_currency', 'created_at')
    search_fields = ('track_id', 'user__email', 'address', 'order_id')
    list_select_related = ('user', 'network', 'topup_intent')
    readonly_fields = ('id', 'track_id', 'address', 'created_at', 'updated_at', 'raw_response')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Payment Details', {
            'fields': ('track_id', 'user', 'network', 'status')
        }),
        ('Amounts', {
            'fields': ('amount', 'currency', 'pay_amount', 'pay_currency')
        }),
        ('Address', {
            'fields': ('address', 'qr_code')
        }),
        ('Metadata', {
            'fields': ('order_id', 'email', 'description', 'callback_url')
        }),
        ('Timing', {
            'fields': ('expired_at',)
        }),
        ('Relations', {
            'fields': ('topup_intent',),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('raw_response',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def track_id_short(self, obj):
        return f"{obj.track_id[:20]}..." if len(obj.track_id) > 20 else obj.track_id
    track_id_short.short_description = 'Track ID'

    def get_amount_display(self, obj):
        return f"{obj.amount} {obj.currency.upper()} → {obj.pay_amount or 'N/A'} {obj.pay_currency.upper()}"
    get_amount_display.short_description = 'Amount'


@admin.register(OxaPayStaticAddress)
class OxaPayStaticAddressAdmin(admin.ModelAdmin):
    list_display = (
        'address_short',
        'user',
        'network',
        'is_active',
        'created_at',
    )
    list_filter = ('network', 'is_active', 'created_at')
    search_fields = ('track_id', 'user__email', 'address', 'order_id')
    list_select_related = ('user', 'network')
    readonly_fields = ('id', 'track_id', 'address', 'qr_code', 'created_at', 'updated_at', 'raw_response')

    fieldsets = (
        ('Address Details', {
            'fields': ('track_id', 'user', 'network', 'address', 'is_active')
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Metadata', {
            'fields': ('order_id', 'email', 'description', 'callback_url')
        }),
        ('Raw Data', {
            'fields': ('raw_response',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def address_short(self, obj):
        return f"{obj.address[:20]}...{obj.address[-10:]}"
    address_short.short_description = 'Address'
