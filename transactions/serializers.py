from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    # Format money fields for frontend
    amount = serializers.SerializerMethodField()
    balance_after = serializers.SerializerMethodField()
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Format date for frontend
    date = serializers.SerializerMethodField()
    # Brand name from related order (if available)
    brand = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id',
            'direction',
            'direction_display',
            'category',
            'category_display',
            'amount',
            'amount_minor',
            'currency_code',
            'description',
            'balance_after',
            'balance_after_minor',
            'status',
            'status_display',
            'related_order_id',
            'related_topup_intent_id',
            'related_onchain_tx_id',
            'brand',
            'date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_amount(self, obj):
        """Format amount as currency string"""
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        sign = '+' if obj.direction == 'credit' else '-'
        return f"{sign}{currency_symbol}{abs(obj.amount_minor) / 100:.2f}"

    def get_balance_after(self, obj):
        """Format balance after as currency string"""
        currency_symbol = {'USD': '$', 'GBP': '£', 'CAD': 'C$'}.get(obj.currency_code, '$')
        return f"{currency_symbol}{obj.balance_after_minor / 100:.2f}"

    def get_date(self, obj):
        """Format date for frontend display"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    def get_brand(self, obj):
        """Get brand name from related order if available"""
        # TODO: When orders app is implemented, fetch brand from order.account.bank.name
        # For now, extract from description if possible
        if obj.category == 'purchase' and obj.description:
            # Try to extract brand from description (e.g., "PlayStation Plus..." -> "PlayStation")
            parts = obj.description.split()
            if parts:
                return parts[0]
        return None

