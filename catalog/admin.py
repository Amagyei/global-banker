from django.contrib import admin
from .models import Country, Bank, Account


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'currency_code', 'is_supported')
    list_filter = ('is_supported',)
    search_fields = ('name', 'code')


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'is_active', 'created_at')
    list_filter = ('country', 'is_active')
    search_fields = ('name',)
    list_select_related = ('country',)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'bank', 'get_country', 'get_currency_code', 'balance_minor', 'price_minor', 'is_active', 'sku', 'created_at')
    list_filter = ('bank__country', 'bank', 'is_active')
    search_fields = ('name', 'description', 'sku')
    list_select_related = ('bank', 'bank__country')
    readonly_fields = ('sku', 'created_at', 'updated_at')

    def get_country(self, obj):
        return obj.bank.country.code
    get_country.short_description = 'Country'
    get_country.admin_order_field = 'bank__country'

    def get_currency_code(self, obj):
        return obj.bank.country.currency_code
    get_currency_code.short_description = 'Currency'
    get_currency_code.admin_order_field = 'bank__country__currency_code'

