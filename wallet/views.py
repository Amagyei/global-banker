from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from .models import Wallet, CryptoNetwork, DepositAddress, TopUpIntent, OnChainTransaction
from .serializers import (
    WalletSerializer,
    CryptoNetworkSerializer,
    DepositAddressSerializer,
    TopUpIntentSerializer,
    OnChainTransactionSerializer,
)
from .utils import create_topup_intent
from .blockchain import BlockchainMonitor


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user wallet"""
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
        return Response([serializer.data])  # Return as list for consistency


class CryptoNetworkViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for cryptocurrency networks"""
    queryset = CryptoNetwork.objects.filter(is_active=True)
    serializer_class = CryptoNetworkSerializer
    permission_classes = [permissions.IsAuthenticated]


class DepositAddressViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for deposit addresses"""
    serializer_class = DepositAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DepositAddress.objects.filter(user=self.request.user, is_active=True)


class TopUpIntentViewSet(viewsets.ModelViewSet):
    """ViewSet for top-up intents"""
    serializer_class = TopUpIntentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TopUpIntent.objects.filter(user=self.request.user).select_related(
            'network', 'deposit_address'
        ).order_by('-created_at')

    def create(self, request):
        """Create a new top-up intent"""
        amount_minor = request.data.get('amount_minor')
        network_id = request.data.get('network_id')
        
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
        
        # Create top-up intent with transaction handling
        # The create_topup_intent function already uses atomic transactions,
        # but we wrap it here for additional safety and error handling
        try:
            with db_transaction.atomic():
                topup = create_topup_intent(
                    user=request.user,
                    amount_minor=amount_minor,
                    network=network
                )
            
            serializer = self.get_serializer(topup)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            # Handle xpub configuration errors and other validation errors
            # Log full error details for backend debugging
            error_msg = str(e)
            logger.error(f"Top-up creation failed: {error_msg}", exc_info=True)
            
            # Return user-friendly error message (hide technical details)
            if 'xpub' in error_msg.lower() or 'DEFAULT_XPUB' in error_msg:
                # Configuration error - don't expose technical details to user
                user_message = "There was a problem creating the payment. Please contact support."
            else:
                # Other validation errors - can be more specific but still user-friendly
                user_message = "There was a problem creating the payment. Please check your input and try again."
            
            return Response(
                {'detail': user_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            # Handle other errors (e.g., database constraints, race conditions)
            # Log full error details for backend debugging
            logger.error(f"Unexpected error creating top-up: {e}", exc_info=True)
            
            # Return generic user-friendly error message
            return Response(
                {'detail': 'There was a problem creating the payment. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def check_status(self, request, pk=None):
        """Manually check status of a top-up intent"""
        topup = self.get_object()
        
        if topup.deposit_address:
            monitor = BlockchainMonitor(topup.network)
            found = monitor.check_deposit_address(topup.deposit_address, topup)
            
            topup.refresh_from_db()
            serializer = self.get_serializer(topup)
            
            return Response({
                'checked': found,
                'topup': serializer.data
            })
        
        return Response({'detail': 'No deposit address found'}, status=status.HTTP_400_BAD_REQUEST)


class OnChainTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for on-chain transactions"""
    serializer_class = OnChainTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OnChainTransaction.objects.filter(
            user=self.request.user
        ).select_related('network', 'topup_intent').order_by('-occurred_at')
