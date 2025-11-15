from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Fulfillment


class CartItemSerializer(serializers.ModelSerializer):
    account_id = serializers.UUIDField(source='account.id', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_description = serializers.CharField(source='account.description', read_only=True)
    account_image_url = serializers.URLField(source='account.image_url', read_only=True)
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'account_id',
            'account_name',
            'account_description',
            'account_image_url',
            'quantity',
            'unit_price',
            'unit_price_minor',
            'total_price',
            'total_price_minor',
            'added_at',
        ]
        read_only_fields = ['id', 'added_at', 'unit_price_minor', 'total_price_minor']

    def get_unit_price(self, obj):
        """All prices are in USD"""
        return f"${obj.unit_price_minor / 100:.2f}"

    def get_total_price(self, obj):
        """All prices are in USD"""
        return f"${obj.total_price_minor / 100:.2f}"


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id',
            'currency_code',
            'items',
            'total',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total(self, obj):
        """All prices are in USD"""
        return f"${obj.total_minor / 100:.2f}"


class OrderItemSerializer(serializers.ModelSerializer):
    account_id = serializers.UUIDField(source='account.id', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_description = serializers.CharField(source='account.description', read_only=True)
    account_bank_name = serializers.CharField(source='account.bank.name', read_only=True)
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'account_id',
            'account_name',
            'account_description',
            'account_bank_name',
            'quantity',
            'unit_price',
            'unit_price_minor',
            'total_price',
            'total_price_minor',
            'metadata',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'unit_price_minor', 'total_price_minor']

    def get_unit_price(self, obj):
        """All prices are in USD"""
        return f"${obj.unit_price_minor / 100:.2f}"

    def get_total_price(self, obj):
        """All prices are in USD"""
        return f"${obj.total_price_minor / 100:.2f}"


class FulfillmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Fulfillment
        fields = [
            'id',
            'status',
            'status_display',
            'delivery_payload',
            'delivered_at',
            'failure_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    fulfillments = FulfillmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    subtotal = serializers.SerializerMethodField()
    fees = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'status_display',
            'subtotal',
            'subtotal_minor',
            'fees',
            'fees_minor',
            'total',
            'total_minor',
            'currency_code',
            'recipient',
            'items',
            'fulfillments',
            'date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']

    def get_subtotal(self, obj):
        """All prices are in USD"""
        return f"${obj.subtotal_minor / 100:.2f}"

    def get_fees(self, obj):
        """All prices are in USD"""
        return f"${obj.fees_minor / 100:.2f}"

    def get_total(self, obj):
        """All prices are in USD"""
        return f"${obj.total_minor / 100:.2f}"

    def get_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

