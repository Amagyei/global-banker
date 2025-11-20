from rest_framework import viewsets, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Country, Bank, Account, fullz, FullzPackage
from .serializers import CountrySerializer, BankSerializer, AccountSerializer, FullzSerializer, FullzPackageSerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing countries - public access"""
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['is_supported']
    search_fields = ['name', 'code']


class BankViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing banks - public access"""
    queryset = Bank.objects.select_related('country').all()
    serializer_class = BankSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['country', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        country_code = self.request.query_params.get('country', None)
        if country_code:
            queryset = queryset.filter(country__code=country_code)
        return queryset


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing bank account products - public access"""
    queryset = Account.objects.select_related('bank', 'bank__country').filter(is_active=True)
    serializer_class = AccountSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['bank', 'is_active']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price_minor', 'balance_minor', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        country_code = self.request.query_params.get('country', None)
        bank_id = self.request.query_params.get('bank', None)
        
        # Filter by country through bank relationship
        if country_code:
            queryset = queryset.filter(bank__country__code=country_code)
        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)
        
        # Exclude accounts that user has already purchased
        if self.request.user.is_authenticated:
            from orders.models import OrderItem
            purchased_account_ids = OrderItem.objects.filter(
                order__user=self.request.user,
                order__status__in=['paid', 'delivered']  # Only exclude if order was paid/delivered
            ).values_list('account_id', flat=True).distinct()
            queryset = queryset.exclude(id__in=purchased_account_ids)
        
        return queryset


class FullzViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing fullz products - public access"""
    queryset = fullz.objects.select_related('bank', 'bank__country').filter(is_active=True)
    serializer_class = FullzSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['bank', 'is_active']
    search_fields = ['name', 'description', 'email', 'ssn']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        country_code = self.request.query_params.get('country', None)
        bank_id = self.request.query_params.get('bank', None)
        
        # Filter by country through bank relationship
        if country_code:
            queryset = queryset.filter(bank__country__code=country_code)
        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)
        
        return queryset


class FullzPackageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing fullz packages - public access"""
    queryset = FullzPackage.objects.select_related('bank', 'bank__country').filter(is_active=True)
    serializer_class = FullzPackageSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['bank', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['price_minor', 'quantity', 'created_at']
    ordering = ['price_minor']

    def get_queryset(self):
        queryset = super().get_queryset()
        country_code = self.request.query_params.get('country', None)
        bank_id = self.request.query_params.get('bank', None)
        
        # Filter by country through bank relationship
        if country_code:
            queryset = queryset.filter(bank__country__code=country_code)
        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)
        
        return queryset
