"""
API v2 Views - OXA Pay integration endpoints
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings
import logging
import json

from .rate_limiting import RateLimitMixin
from .address_validation import AddressValidator, validate_deposit_address
from .fee_estimation import FeeEstimator, get_recommended_fee

logger = logging.getLogger(__name__)

from .models import (
    Wallet, CryptoNetwork, TopUpIntent, OxaPayPayment, OxaPayStaticAddress
)
from .serializers import (
    WalletSerializer,
    CryptoNetworkSerializer,
    TopUpIntentSerializer,
    OxaPayPaymentSerializer,
    OxaPayStaticAddressSerializer,
)
from .oxa_pay_client import OxaPayClient
from .utils import create_topup_intent
from django.conf import settings


class WalletV2ViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user wallet (v2 - same as v1)"""
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        wallet, _ = Wallet.objects.get_or_create(
            user=self.request.user,
            defaults={'currency_code': 'USD', 'balance_minor': 0}
        )
        return Wallet.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        """Return single wallet object (not a list)"""
        wallet, _ = Wallet.objects.get_or_create(
            user=request.user,
            defaults={'currency_code': 'USD', 'balance_minor': 0}
        )
        serializer = self.get_serializer(wallet)
        return Response([serializer.data])


class CryptoNetworkV2ViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for cryptocurrency networks (v2 - same as v1)"""
    queryset = CryptoNetwork.objects.filter(is_active=True)
    serializer_class = CryptoNetworkSerializer
    permission_classes = [permissions.IsAuthenticated]


class TopUpIntentV2ViewSet(RateLimitMixin, viewsets.ModelViewSet):
    """ViewSet for top-up intents using OXA Pay (v2)"""
    serializer_class = TopUpIntentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Rate limits for top-up operations
    rate_limits = {
        'list': '60/m',
        'retrieve': '60/m',
        'create': '10/m',  # Limit payment creation
    }

    def get_queryset(self):
        return TopUpIntent.objects.filter(user=self.request.user).select_related(
            'network', 'deposit_address'
        ).order_by('-created_at')

    def create(self, request):
        """Create a new top-up intent using OXA Pay"""
        amount_minor = request.data.get('amount_minor')
        network_id = request.data.get('network_id')
        use_static_address = request.data.get('use_static_address', False)  # Reuse static address
        
        if not amount_minor or not network_id:
            return Response(
                {'detail': 'amount_minor and network_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            network = CryptoNetwork.objects.get(id=network_id, is_active=True)
        except CryptoNetwork.DoesNotExist:
            return Response(
                {'detail': 'Network not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            amount_minor = int(amount_minor)
            if amount_minor <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'detail': 'amount_minor must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert amount_minor (cents) to decimal amount
        amount_usd = float(amount_minor) / 100
        
        try:
            # Initialize OXA Pay client
            oxa_client = OxaPayClient()
            
            # Get callback URL from settings or construct it
            callback_url = getattr(settings, 'OXAPAY_CALLBACK_URL', None)
            if not callback_url:
                # Construct callback URL from request
                scheme = request.scheme
                host = request.get_host()
                callback_url = f"{scheme}://{host}/api/v2/wallet/webhook/"
            
            # Determine payment currency
            # For tokens (USDT, USDC), use the token symbol directly as pay_currency
            # OXA Pay handles token payments by using the token symbol, not the native coin
            # For native coins (BTC, ETH, BNB, SOL, LTC), pay_currency is the coin itself
            to_currency = None
            if network.native_symbol.upper() in ['USDT', 'USDC']:
                # For tokens, use the token symbol as pay_currency
                # OXA Pay will handle the network routing based on network parameter
                pay_currency = network.native_symbol.lower()  # 'usdt' or 'usdc'
                # to_currency is not needed when pay_currency is the token itself
            else:
                # Native coins: BTC, ETH, BNB, SOL, LTC
                pay_currency = network.native_symbol.lower()
            
            # Check if we should use static address
            static_address = None
            if use_static_address:
                static_address = OxaPayStaticAddress.objects.filter(
                    user=request.user,
                    network=network,
                    is_active=True
                ).first()
            
            with db_transaction.atomic():
                # For OXA Pay, we don't need to derive addresses from xpub
                # OXA Pay generates addresses for us via their API
                # Create top-up intent without deposit address (OXA Pay will provide it)
                from wallet.models import TopUpIntent
                topup = TopUpIntent.objects.create(
                    user=request.user,
                    amount_minor=amount_minor,
                    currency_code='USD',
                    network=network,
                    deposit_address=None,  # OXA Pay provides address, not derived from xpub
                    status='pending'
                )
                
                # Generate OXA Pay payment
                if static_address:
                    # Use existing static address
                    oxa_payment = OxaPayPayment.objects.create(
                        user=request.user,
                        topup_intent=topup,
                        track_id=static_address.track_id,
                        network=network,
                        address=static_address.address,
                        amount=amount_usd,
                        pay_currency=pay_currency,
                        currency='usd',
                        status='pending',
                        callback_url=callback_url,
                        order_id=str(topup.id),
                        email=request.user.email,
                        description=f'Top-up for {request.user.email}',
                        qr_code=static_address.qr_code,
                        raw_response={'using_static_address': True}
                    )
                else:
                    # Generate new white-label payment for wallet top-up
                    # Map network key to OXA Pay network name
                    # For tokens, we need both network and to_currency
                    network_map = {
                        'btc': 'Bitcoin Network',
                        'eth': 'Ethereum Network',
                        'usdt': 'TRON',  # USDT on TRON (default)
                        'usdc': 'Ethereum Network',  # USDC on Ethereum
                        'bnb': 'Binance Smart Chain',
                        'sol': 'Solana Network',
                        'ltc': 'Litecoin Network',
                    }
                    oxa_network = network_map.get(network.key.lower(), network.name)
                    
                    try:
                        # For white-label payments, OXA Pay may not require network field
                        # when pay_currency is specified. Let's try without network first for tokens.
                        # If that fails, we'll add it back.
                        payment_kwargs = {
                            'amount': amount_usd,
                            'pay_currency': pay_currency,
                            'currency': 'usd',
                            'lifetime': 60,  # 60 minutes expiration
                            'callback_url': callback_url,
                            'order_id': f'TOPUP-{topup.id}',
                            'email': request.user.email,
                            'description': f'Wallet Top-up: ${amount_usd:.2f} USD - User: {request.user.email} - Network: {network.name} ({network.native_symbol})',
                            'auto_withdrawal': True,  # Auto-withdraw to cold wallet
                            'under_paid_coverage': 1.0,  # 1% tolerance
                        }
                        
                        # Only add network for tokens if needed (OXA Pay might infer it from pay_currency)
                        # For native coins, network might be optional
                        if network.native_symbol.upper() in ['USDT', 'USDC']:
                            # For tokens, network helps specify which blockchain (TRON for USDT, Ethereum for USDC)
                            payment_kwargs['network'] = oxa_network
                        
                        # Log the request for debugging
                        logger.info(f"Creating OXA Pay payment for {network.native_symbol}: {json.dumps(payment_kwargs, indent=2)}")
                        
                        oxa_data = oxa_client.generate_white_label_payment(**payment_kwargs)
                        
                        # Log the response for debugging
                        logger.info(f"OXA Pay payment created successfully: track_id={oxa_data.get('track_id')}, address={oxa_data.get('address')}, network={network.name}")
                        
                        # Parse expired_at from UNIX timestamp (make timezone-aware)
                        expired_at = None
                        if oxa_data.get('expired_at'):
                            from datetime import datetime
                            from django.utils import timezone
                            # Convert UNIX timestamp to timezone-aware datetime
                            expired_at = timezone.make_aware(
                                datetime.fromtimestamp(oxa_data['expired_at'])
                            )
                        
                        oxa_payment = OxaPayPayment.objects.create(
                            user=request.user,
                            topup_intent=topup,
                            track_id=oxa_data.get('track_id', ''),
                            network=network,
                            address=oxa_data.get('address', ''),
                            amount=float(oxa_data.get('amount', amount_usd)),
                            pay_amount=float(oxa_data.get('pay_amount', 0)) if oxa_data.get('pay_amount') else None,
                            pay_currency=oxa_data.get('pay_currency', pay_currency),
                            currency=oxa_data.get('currency', 'usd'),
                            status='pending',
                            callback_url=callback_url,
                            order_id=f'TOPUP-{topup.id}',
                            email=request.user.email,
                            description=f'Wallet Top-up: ${amount_usd:.2f} USD - User: {request.user.email} - Network: {network.name} ({network.native_symbol})',
                            expired_at=expired_at,
                            qr_code=oxa_data.get('qr_code', ''),
                            raw_response=oxa_data
                        )
                    except Exception as e:
                        logger.error(f"OXA Pay payment creation failed: {e}", exc_info=True)
                        return Response(
                            {'detail': 'Failed to create payment. Please try again or try another network'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
            
            # Return combined response
            serializer = self.get_serializer(topup)
            oxa_serializer = OxaPayPaymentSerializer(oxa_payment)
            
            return Response({
                'topup': serializer.data,
                'payment': oxa_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            logger.error(f"Top-up creation failed: {e}", exc_info=True)
            return Response(
                {'detail': 'There was a problem creating the payment. Please contact support.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error creating top-up: {e}", exc_info=True)
            return Response(
                {'detail': 'There was a problem creating the payment. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OxaPayPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for OXA Pay payment records"""
    serializer_class = OxaPayPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OxaPayPayment.objects.filter(user=self.request.user).select_related(
            'network', 'topup_intent'
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def accepted_currencies(self, request):
        """Get list of accepted currencies from OXA Pay"""
        try:
            oxa_client = OxaPayClient()
            currencies = oxa_client.get_accepted_currencies()
            return Response(currencies, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get accepted currencies: {e}", exc_info=True)
            return Response(
                {'detail': 'Failed to get accepted currencies. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def accepted_currencies(self, request):
        """Get list of accepted currencies from OXA Pay"""
        try:
            oxa_client = OxaPayClient()
            currencies = oxa_client.get_accepted_currencies()
            return Response(currencies, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get accepted currencies: {e}", exc_info=True)
            return Response(
                {'detail': 'Failed to get accepted currencies. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OxaPayStaticAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for OXA Pay static addresses"""
    serializer_class = OxaPayStaticAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OxaPayStaticAddress.objects.filter(user=self.request.user).select_related(
            'network'
        ).order_by('-created_at')

    def create(self, request):
        """Create a new static address via OXA Pay"""
        network_id = request.data.get('network_id')
        
        if not network_id:
            return Response(
                {'detail': 'network_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            network = CryptoNetwork.objects.get(id=network_id, is_active=True)
        except CryptoNetwork.DoesNotExist:
            return Response(
                {'detail': 'Network not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if static address already exists for this user/network
        existing = OxaPayStaticAddress.objects.filter(
            user=request.user,
            network=network,
            is_active=True
        ).first()
        
        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        try:
            # Initialize OXA Pay client
            oxa_client = OxaPayClient()
            
            # Get callback URL
            callback_url = getattr(settings, 'OXAPAY_CALLBACK_URL', None)
            if not callback_url:
                scheme = request.scheme
                host = request.get_host()
                callback_url = f"{scheme}://{host}/api/v2/wallet/webhook/"
            
            # Map network key to OXA Pay network name (for static addresses)
            network_map_static = {
                'btc': 'Bitcoin Network',
                'eth': 'Ethereum Network',
                'usdt': 'TRON',  # USDT on TRON
                'usdc': 'Ethereum Network',  # USDC on Ethereum
                'bnb': 'Binance Smart Chain',
                'sol': 'Solana Network',
                'ltc': 'Litecoin Network',
            }
            oxa_network = network_map_static.get(network.key.lower(), network.name)
            
            # Generate static address
            # For static addresses, network is required and to_currency specifies the token
            static_address_kwargs = {
                'network': oxa_network,
                'callback_url': callback_url,
                'email': request.user.email,
                'description': f'Static address for {request.user.email}',
                'auto_withdrawal': True,
            }
            
            # For tokens, add to_currency parameter
            if network.native_symbol.upper() in ['USDT', 'USDC']:
                static_address_kwargs['to_currency'] = network.native_symbol.upper()
            
            oxa_data = oxa_client.generate_static_address(**static_address_kwargs)
            
            # Create static address record
            static_address = OxaPayStaticAddress.objects.create(
                user=request.user,
                network=network,
                track_id=oxa_data.get('track_id', ''),
                address=oxa_data.get('address', ''),
                callback_url=callback_url,
                email=request.user.email,
                description=f'Static address for {request.user.email}',
                qr_code=oxa_data.get('qr_code', ''),
                raw_response=oxa_data
            )
            
            serializer = self.get_serializer(static_address)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create OXA Pay static address: {e}", exc_info=True)
            return Response(
                {'detail': 'Failed to create static address. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OxaPayInvoiceViewSet(viewsets.ViewSet):
    """ViewSet for OXA Pay invoice generation"""
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request):
        """Generate an OXA Pay invoice"""
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'usd')
        lifetime = request.data.get('lifetime', 60)
        callback_url = request.data.get('callback_url')
        return_url = request.data.get('return_url')
        order_id = request.data.get('order_id')
        email = request.data.get('email', request.user.email)
        description = request.data.get('description')
        thanks_message = request.data.get('thanks_message')
        fee_paid_by_payer = request.data.get('fee_paid_by_payer')
        under_paid_coverage = request.data.get('under_paid_coverage')
        to_currency = request.data.get('to_currency')
        auto_withdrawal = request.data.get('auto_withdrawal', True)
        mixed_payment = request.data.get('mixed_payment')
        sandbox = request.data.get('sandbox', False)
        
        if not amount:
            return Response(
                {'detail': 'amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'detail': 'amount must be a positive number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            oxa_client = OxaPayClient()
            
            # Get callback URL if not provided
            if not callback_url:
                callback_url = getattr(settings, 'OXAPAY_CALLBACK_URL', None)
                if not callback_url:
                    scheme = request.scheme
                    host = request.get_host()
                    callback_url = f"{scheme}://{host}/api/v2/wallet/webhook/"
            
            # Generate invoice
            invoice_data = oxa_client.generate_invoice(
                amount=amount,
                currency=currency,
                lifetime=lifetime,
                callback_url=callback_url,
                return_url=return_url,
                order_id=order_id,
                email=email,
                description=description,
                thanks_message=thanks_message,
                fee_paid_by_payer=fee_paid_by_payer,
                under_paid_coverage=under_paid_coverage,
                to_currency=to_currency,
                auto_withdrawal=auto_withdrawal,
                mixed_payment=mixed_payment,
                sandbox=sandbox
            )
            
            return Response(invoice_data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            logger.error(f"Invoice generation failed: {e}", exc_info=True)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Failed to generate invoice: {e}", exc_info=True)
            return Response(
                {'detail': 'Failed to generate invoice. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddressValidationViewSet(viewsets.ViewSet):
    """ViewSet for address validation"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """
        Validate a cryptocurrency address.
        
        Request body:
        {
            "address": "bc1q...",
            "network_key": "btc",
            "is_testnet": false
        }
        """
        address = request.data.get('address')
        network_key = request.data.get('network_key')
        is_testnet = request.data.get('is_testnet', False)
        
        if not address or not network_key:
            return Response(
                {'detail': 'address and network_key are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_valid, error = validate_deposit_address(address, network_key, is_testnet)
        address_type = AddressValidator.get_address_type(address, network_key)
        
        return Response({
            'is_valid': is_valid,
            'error': error,
            'address_type': address_type,
            'network_key': network_key,
            'is_testnet': is_testnet,
        })


class FeeEstimationViewSet(viewsets.ViewSet):
    """ViewSet for fee estimation"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def estimate(self, request):
        """
        Get fee estimates for a network.
        
        Query params:
        - network_key: btc, eth, ltc, etc.
        - is_testnet: true/false (default: false)
        - priority: fast, medium, slow (default: medium)
        - tx_type: p2wpkh, transfer, erc20 (default: p2wpkh)
        """
        network_key = request.query_params.get('network_key', 'btc')
        is_testnet = request.query_params.get('is_testnet', 'false').lower() == 'true'
        priority = request.query_params.get('priority', 'medium')
        tx_type = request.query_params.get('tx_type', 'p2wpkh')
        
        # Get fee estimates
        fees = get_recommended_fee(network_key, is_testnet, priority)
        
        # Get transaction fee estimate
        tx_fee, description = FeeEstimator.estimate_transaction_fee(
            network_key=network_key,
            is_testnet=is_testnet,
            priority=priority,
            tx_type=tx_type
        )
        
        return Response({
            'network_key': network_key,
            'is_testnet': is_testnet,
            'fee_rates': fees,
            'transaction_fee': {
                'amount': tx_fee,
                'description': description,
                'priority': priority,
                'tx_type': tx_type,
            }
        })

