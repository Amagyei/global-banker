from rest_framework import serializers
from .models import Country, Bank, Account


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['code', 'name', 'currency_code', 'flag_url', 'is_supported']


class BankSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source='country.code', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Bank
        fields = [
            'id',
            'name',
            'logo_url',
            'country_code',
            'country_name',
            'is_active',
            'created_at',
            'updated_at',
        ]


class AccountSerializer(serializers.ModelSerializer):
    bank_id = serializers.UUIDField(source='bank.id', read_only=True)
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    country_code = serializers.SerializerMethodField()  # From bank.country
    country_name = serializers.SerializerMethodField()  # From bank.country
    currency_code = serializers.SerializerMethodField()  # From bank.country.currency_code
    # Format money fields for frontend
    balance = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id',
            'sku',
            'name',
            'description',
            'bank_id',
            'bank_name',
            'country_code',
            'country_name',
            'balance',
            'balance_minor',
            'price',
            'price_minor',
            'currency_code',
            'image_url',
            'is_active',
            'metadata',
            'created_at',
            'updated_at',
        ]

    def get_country_code(self, obj):
        """Get country code from bank's country"""
        return obj.bank.country.code

    def get_country_name(self, obj):
        """Get country name from bank's country"""
        return obj.bank.country.name

    def get_currency_code(self, obj):
        """Get currency code from bank's country"""
        return obj.bank.country.currency_code

    def get_balance(self, obj):
        """Format balance as currency string - uses account's currency"""
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        return f"{currency_symbol}{obj.balance_minor / 100:.2f}"

    def get_price(self, obj):
        """Format price as currency string - ALWAYS USD for sales"""
        # All prices are in USD regardless of account currency
        return f"${obj.price_minor / 100:.2f}"

