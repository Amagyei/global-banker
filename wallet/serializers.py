from rest_framework import serializers
from .models import Wallet, CryptoNetwork, DepositAddress, TopUpIntent, OnChainTransaction


class CryptoNetworkSerializer(serializers.ModelSerializer):
    # Use effective testnet status (respects WALLET_TEST_MODE)
    is_testnet = serializers.SerializerMethodField()
    
    class Meta:
        model = CryptoNetwork
        fields = [
            'id',
            'key',
            'name',
            'native_symbol',
            'decimals',
            'is_testnet',
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
        return f"${obj.amount_minor / 100:.2f}"


class TopUpIntentSerializer(serializers.ModelSerializer):
    network = CryptoNetworkSerializer(read_only=True)
    deposit_address = DepositAddressSerializer(read_only=True)
    amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    qr_code_data = serializers.SerializerMethodField()
    expires_in_minutes = serializers.SerializerMethodField()

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
            'expires_in_minutes',
            'expires_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_amount(self, obj):
        """Format amount as currency string"""
        return f"${obj.amount_minor / 100:.2f}"

    def get_qr_code_data(self, obj):
        """Generate QR code data URI for deposit address"""
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

    def get_expires_in_minutes(self, obj):
        """Calculate minutes until expiration"""
        from django.utils import timezone
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return max(0, int(delta.total_seconds() / 60))
        return 0


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
        return f"${obj.balance_minor / 100:.2f}"

    def get_pending(self, obj):
        """Format pending as currency string"""
        return f"${obj.pending_minor / 100:.2f}"

