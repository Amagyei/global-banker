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
        """Add item to cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        account_id = request.data.get('account_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not account_id:
            return Response({'detail': 'account_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from catalog.models import Account
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
            defaults={
                'quantity': quantity,
                'unit_price_minor': account.price_minor,
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
        return CartItem.objects.filter(cart=cart).select_related('account')

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
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'items__account', 'items__account__bank', 'fulfillments')

    def create(self, request):
        """Create order from cart"""
        from wallet.models import Wallet
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        if not cart.items.exists():
            return Response({'detail': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        recipient = request.data.get('recipient', {})
        if not recipient:
            return Response({'detail': 'Recipient information is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            # Calculate totals
            subtotal_minor = cart.total_minor
            fees_minor = 0  # No fees for now
            total_minor = subtotal_minor + fees_minor
            
            # Check wallet balance
            wallet, _ = Wallet.objects.get_or_create(
                user=request.user,
                defaults={'currency_code': 'USD', 'balance_minor': 0}
            )
            
            if wallet.balance_minor < total_minor:
                return Response(
                    {
                        'detail': 'Insufficient wallet balance',
                        'required': total_minor / 100,
                        'available': wallet.balance_minor / 100,
                        'shortfall': (total_minor - wallet.balance_minor) / 100,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                subtotal_minor=subtotal_minor,
                fees_minor=fees_minor,
                total_minor=total_minor,
                currency_code=cart.currency_code,
                recipient=recipient,
                status='pending',
            )
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    account=cart_item.account,
                    quantity=cart_item.quantity,
                    unit_price_minor=cart_item.unit_price_minor,
                )
            
            # Deduct from wallet
            wallet.balance_minor -= total_minor
            wallet.save()
            
            # Create transaction (debit)
            Transaction.objects.create(
                user=request.user,
                direction='debit',
                category='purchase',
                amount_minor=total_minor,
                currency_code=cart.currency_code,
                description=f'Order {order.order_number}',
                balance_after_minor=wallet.balance_minor,
                status='completed',  # Auto-complete since wallet has funds
                related_order_id=order.id,
            )
            
            # Mark order as paid
            order.status = 'paid'
            order.save()
            
            # Clear cart
            cart.items.all().delete()
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
