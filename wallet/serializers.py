from rest_framework import serializers
from .models import (
    Wallet, CryptoNetwork, DepositAddress, TopUpIntent, OnChainTransaction,
    OxaPayPayment, OxaPayStaticAddress
)


class CryptoNetworkSerializer(serializers.ModelSerializer):
    # Use effective testnet status (respects WALLET_TEST_MODE)
    is_testnet = serializers.SerializerMethodField()
    # Expose actual database is_testnet value (for OXA Pay filtering)
    db_is_testnet = serializers.BooleanField(source='is_testnet', read_only=True)
    
    class Meta:
        model = CryptoNetwork
        fields = [
            'id',
            'key',
            'name',
            'native_symbol',
            'decimals',
            'is_testnet',
            'db_is_testnet',
            'is_active',
            'required_confirmations',
        ]
    
    def get_is_testnet(self, obj):
        """Return effective testnet status (respects WALLET_TEST_MODE)"""
        return obj.effective_is_testnet


class DepositAddressSerializer(serializers.ModelSerializer):
    network_name = serializers.CharField(source='network.name', read_only=True)
    network_symbol = serializers.CharField(source='network.native_symbol', read_only=True)

    class Meta:
        model = DepositAddress
        fields = [
            'id',
            'address',
            'network_name',
            'network_symbol',
            'memo_tag',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class OnChainTransactionSerializer(serializers.ModelSerializer):
    network_name = serializers.CharField(source='network.name', read_only=True)
    network_symbol = serializers.CharField(source='network.native_symbol', read_only=True)
    amount_crypto = serializers.SerializerMethodField()
    amount_usd = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OnChainTransaction
        fields = [
            'id',
            'tx_hash',
            'network_name',
            'network_symbol',
            'from_address',
            'to_address',
            'amount_crypto',
            'amount_atomic',
            'amount_usd',
            'amount_minor',
            'confirmations',
            'required_confirmations',
            'status',
            'status_display',
            'occurred_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_amount_crypto(self, obj):
        """Format amount in native crypto currency"""
        decimals = obj.network.decimals
        amount = obj.amount_atomic / (10 ** decimals)
        return f"{amount:.{min(decimals, 8)}f} {obj.network.native_symbol}"

    def get_amount_usd(self, obj):
        """Format amount in USD"""
        return f"${obj.amount_minor.amount:.2f}"


class TopUpIntentSerializer(serializers.ModelSerializer):
    network = CryptoNetworkSerializer(read_only=True)
    deposit_address = DepositAddressSerializer(read_only=True)
    amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    qr_code_data = serializers.SerializerMethodField()

    class Meta:
        model = TopUpIntent
        fields = [
            'id',
            'amount',
            'amount_minor',
            'currency_code',
            'network',
            'deposit_address',
            'status',
            'status_display',
            'qr_code_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_amount(self, obj):
        """Format amount as currency string"""
        return f"${obj.amount_minor.amount:.2f}"

    def get_qr_code_data(self, obj):
        """Generate QR code data URI for deposit address"""
        # For OXA Pay, deposit_address may be None (address comes from OXA Pay)
        if not obj.deposit_address:
            # Return None - OXA Pay provides QR code separately
            return None
        
        # Format: network:address?amount=...
        network = obj.network
        address = obj.deposit_address.address
        
        # Calculate crypto amount (placeholder - would need exchange rate)
        # For now, return address only
        if network.key.lower() == 'btc':
            return f"bitcoin:{address}"
        elif network.key.lower() in ['eth', 'ethereum']:
            return f"ethereum:{address}"
        else:
            return address


class WalletSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    pending = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            'id',
            'currency_code',
            'balance',
            'balance_minor',
            'pending',
            'pending_minor',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']

    def get_balance(self, obj):
        """Format balance as currency string"""
        return obj.balance_minor.amount

    def get_pending(self, obj):
        """Format pending as currency string"""
        return obj.pending_minor.amount


class OxaPayPaymentSerializer(serializers.ModelSerializer):
    """Serializer for OXA Pay payment records"""
    network = CryptoNetworkSerializer(read_only=True)
    amount_display = serializers.SerializerMethodField()
    pay_amount_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = OxaPayPayment
        fields = [
            'id',
            'track_id',
            'network',
            'address',
            'amount',
            'amount_display',
            'pay_amount',
            'pay_amount_display',
            'pay_currency',
            'currency',
            'status',
            'status_display',
            'qr_code',
            'expired_at',
            'is_expired',
            'order_id',
            'email',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'track_id', 'address', 'created_at', 'updated_at']

    def get_amount_display(self, obj):
        """Format amount in invoice currency"""
        return f"{obj.amount} {obj.currency.upper()}"

    def get_pay_amount_display(self, obj):
        """Format payment amount in crypto currency"""
        if obj.pay_amount:
            return f"{obj.pay_amount} {obj.pay_currency.upper()}"
        return None

    def get_is_expired(self, obj):
        """Check if payment is expired"""
        from django.utils import timezone
        if obj.expired_at:
            # Handle both naive and aware datetimes
            expired = obj.expired_at
            if timezone.is_naive(expired):
                expired = timezone.make_aware(expired)
            return timezone.now() > expired
        return False


class OxaPayStaticAddressSerializer(serializers.ModelSerializer):
    """Serializer for OXA Pay static addresses"""
    network = CryptoNetworkSerializer(read_only=True)

    class Meta:
        model = OxaPayStaticAddress
        fields = [
            'id',
            'track_id',
            'network',
            'address',
            'qr_code',
            'order_id',
            'email',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'track_id', 'address', 'qr_code', 'created_at', 'updated_at']

