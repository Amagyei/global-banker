from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Fulfillment


class CartItemSerializer(serializers.ModelSerializer):
    # Account fields (nullable)
    account_id = serializers.UUIDField(source='account.id', read_only=True, allow_null=True)
    account_name = serializers.CharField(source='account.name', read_only=True, allow_null=True)
    account_description = serializers.CharField(source='account.description', read_only=True, allow_null=True)
    account_image_url = serializers.URLField(source='account.image_url', read_only=True, allow_null=True)
    # FullzPackage fields (nullable)
    fullz_package_id = serializers.UUIDField(source='fullz_package.id', read_only=True, allow_null=True)
    fullz_package_name = serializers.CharField(source='fullz_package.name', read_only=True, allow_null=True)
    fullz_package_description = serializers.CharField(source='fullz_package.description', read_only=True, allow_null=True)
    fullz_package_quantity = serializers.IntegerField(source='fullz_package.quantity', read_only=True, allow_null=True)
    # Item type indicator
    item_type = serializers.SerializerMethodField()
    item_name = serializers.SerializerMethodField()
    item_description = serializers.SerializerMethodField()
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
            'fullz_package_id',
            'fullz_package_name',
            'fullz_package_description',
            'fullz_package_quantity',
            'item_type',
            'item_name',
            'item_description',
            'quantity',
            'unit_price',
            'unit_price_minor',
            'total_price',
            'total_price_minor',
            'added_at',
        ]
        read_only_fields = ['id', 'added_at', 'unit_price_minor', 'total_price_minor']

    def get_item_type(self, obj):
        """Return 'account' or 'fullz_package'"""
        return 'account' if obj.account else 'fullz_package'

    def get_item_name(self, obj):
        """Return name from account or package"""
        return obj.account.name if obj.account else (obj.fullz_package.name if obj.fullz_package else None)

    def get_item_description(self, obj):
        """Return description from account or package"""
        if obj.account:
            return obj.account.description
        elif obj.fullz_package:
            return f"{obj.fullz_package.name} - {obj.fullz_package.quantity} fullz"
        return None

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
    # Account fields (nullable)
    account_id = serializers.UUIDField(source='account.id', read_only=True, allow_null=True)
    account_name = serializers.CharField(source='account.name', read_only=True, allow_null=True)
    account_description = serializers.CharField(source='account.description', read_only=True, allow_null=True)
    account_bank_name = serializers.CharField(source='account.bank.name', read_only=True, allow_null=True)
    # FullzPackage fields (nullable)
    fullz_package_id = serializers.UUIDField(source='fullz_package.id', read_only=True, allow_null=True)
    fullz_package_name = serializers.CharField(source='fullz_package.name', read_only=True, allow_null=True)
    fullz_package_description = serializers.CharField(source='fullz_package.description', read_only=True, allow_null=True)
    fullz_package_quantity = serializers.IntegerField(source='fullz_package.quantity', read_only=True, allow_null=True)
    fullz_package_bank_name = serializers.CharField(source='fullz_package.bank.name', read_only=True, allow_null=True)
    # Item type indicator
    item_type = serializers.SerializerMethodField()
    item_name = serializers.SerializerMethodField()
    item_description = serializers.SerializerMethodField()
    item_bank_name = serializers.SerializerMethodField()
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
            'fullz_package_id',
            'fullz_package_name',
            'fullz_package_description',
            'fullz_package_quantity',
            'fullz_package_bank_name',
            'item_type',
            'item_name',
            'item_description',
            'item_bank_name',
            'quantity',
            'unit_price',
            'unit_price_minor',
            'total_price',
            'total_price_minor',
            'metadata',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'unit_price_minor', 'total_price_minor']

    def get_item_type(self, obj):
        """Return 'account' or 'fullz_package'"""
        return 'account' if obj.account else 'fullz_package'

    def get_item_name(self, obj):
        """Return name from account or package"""
        return obj.account.name if obj.account else (obj.fullz_package.name if obj.fullz_package else None)

    def get_item_description(self, obj):
        """Return description from account or package"""
        if obj.account:
            return obj.account.description
        elif obj.fullz_package:
            return f"{obj.fullz_package.name} - {obj.fullz_package.quantity} fullz"
        return None

    def get_item_bank_name(self, obj):
        """Return bank name from account or package"""
        if obj.account:
            return obj.account.bank.name
        elif obj.fullz_package:
            return obj.fullz_package.bank.name
        return None

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

