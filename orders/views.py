from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import Cart, CartItem, Order, OrderItem, Fulfillment
from .serializers import CartSerializer, CartItemSerializer, OrderSerializer
from transactions.models import Transaction


class CartViewSet(viewsets.ModelViewSet):
    """ViewSet for cart management"""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get or create cart for current user"""
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return Cart.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='items')
    def add_item(self, request):
        """Add item to cart - supports both Account and FullzPackage"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        account_id = request.data.get('account_id')
        fullz_package_id = request.data.get('fullz_package_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not account_id and not fullz_package_id:
            return Response({'detail': 'account_id or fullz_package_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if account_id and fullz_package_id:
            return Response({'detail': 'Cannot specify both account_id and fullz_package_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        from catalog.models import Account, FullzPackage
        
        if account_id:
            # Handle Account
            try:
                account = Account.objects.get(id=account_id, is_active=True)
            except Account.DoesNotExist:
                return Response({'detail': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user has already purchased this account
            already_purchased = OrderItem.objects.filter(
                order__user=request.user,
                order__status__in=['paid', 'delivered'],
                account=account
            ).exists()
            
            if already_purchased:
                return Response(
                    {'detail': 'You have already purchased this account'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                account=account,
                fullz_package=None,
                defaults={
                    'quantity': quantity,
                    'unit_price_minor': account.price_minor.amount,
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
        else:
            # Handle FullzPackage
            try:
                fullz_package = FullzPackage.objects.get(id=fullz_package_id, is_active=True)
            except FullzPackage.DoesNotExist:
                return Response({'detail': 'FullzPackage not found'}, status=status.HTTP_404_NOT_FOUND)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                account=None,
                fullz_package=fullz_package,
                defaults={
                    'quantity': quantity,
                    'unit_price_minor': fullz_package.price_minor.amount,
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CartItemViewSet(viewsets.ModelViewSet):
    """ViewSet for cart items"""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart).select_related('account', 'fullz_package', 'fullz_package__bank')

    def update(self, request, *args, **kwargs):
        """Update cart item quantity"""
        quantity = request.data.get('quantity')
        if quantity is not None:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            instance.quantity = int(quantity)
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return super().update(request, *args, **kwargs)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for orders"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items', 
            'items__account', 
            'items__account__bank', 
            'items__fullz_package',
            'items__fullz_package__bank',
            'fulfillments'
        )

    def create(self, request):
        """Create order from cart
        
        If payment_method is 'oxapay', order is created with status 'pending' and 
        will be marked as 'paid' when OXA Pay webhook confirms payment.
        Otherwise, order is created and wallet is deducted immediately.
        """
        from wallet.models import Wallet
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        if not cart.items.exists():
            return Response({'detail': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        recipient = request.data.get('recipient', {})
        if not recipient:
            return Response({'detail': 'Recipient information is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_method = request.data.get('payment_method', 'wallet')  # 'wallet' or 'oxapay'
        
        with db_transaction.atomic():
            # Calculate totals
            subtotal_minor = cart.total_minor
            fees_minor = 0  # No fees for now
            total_minor = subtotal_minor + fees_minor
            
            # Create order (status will be 'pending' for oxapay/crypto, 'paid' for wallet after payment)
            order = Order.objects.create(
                user=request.user,
                subtotal_minor=subtotal_minor,
                fees_minor=fees_minor,
                total_minor=total_minor,
                currency_code=cart.currency_code,
                recipient=recipient,
                status='pending',  # Will be updated to 'paid' for wallet payment below
            )
            
            # Create order items (supports both Account and FullzPackage)
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    account=cart_item.account,
                    fullz_package=cart_item.fullz_package,
                    quantity=cart_item.quantity,
                    unit_price_minor=cart_item.unit_price_minor,
                )
            
            # If wallet payment, deduct immediately
            if payment_method == 'wallet':
                wallet, _ = Wallet.objects.get_or_create(
                    user=request.user,
                    defaults={'currency_code': 'USD', 'balance_minor': 0}
                )
                
                # All fields are now MoneyField (dollars) - direct comparison
                # total_minor is Decimal from Cart property
                from decimal import Decimal
                total_decimal = Decimal(str(total_minor))
                
                if wallet.balance_minor.amount < total_decimal:
                    return Response(
                        {
                            'detail': 'Insufficient wallet balance',
                            'required': float(total_decimal),
                            'available': float(wallet.balance_minor.amount),
                            'shortfall': float(total_decimal) - float(wallet.balance_minor.amount),
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Deduct from wallet - subtract the decimal amount
                wallet.balance_minor = wallet.balance_minor.amount - total_decimal
                wallet.save()
                
                # Create transaction (debit) - all MoneyFields now
                Transaction.objects.create(
                    user=request.user,
                    direction='debit',
                    category='purchase',
                    amount_minor=total_decimal,
                    currency_code=cart.currency_code,
                    description=f'Order {order.order_number}',
                    balance_after_minor=wallet.balance_minor.amount,
                    status='completed',
                    related_order_id=order.id,
                )
                
                # Mark order as paid
                order.status = 'paid'
                order.save()
                
                # Send order confirmation email to ALL confirmed purchases
                try:
                    from notifications.services import send_order_confirmation_email
                    send_order_confirmation_email(order)
                except Exception as e:
                    # Log error but don't fail order creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send order confirmation email for order {order.order_number}: {e}")
                
                # Clear cart
                cart.items.all().delete()
            else:
                # For OXA Pay, order stays 'pending' until webhook confirms payment
                # Don't clear cart yet - will be cleared when payment is confirmed
                pass
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
