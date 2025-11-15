from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.utils import timezone
from datetime import timedelta

from .models import Transaction
from .serializers import TransactionSerializer


class TransactionFilter(django_filters.FilterSet):
    """Custom filters for transactions"""
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    min_amount = django_filters.NumberFilter(field_name='amount_minor', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount_minor', lookup_expr='lte')

    class Meta:
        model = Transaction
        fields = ['direction', 'category', 'status', 'currency_code']


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing transactions"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ['description']
    ordering_fields = ['created_at', 'amount_minor']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter transactions to current user only"""
        queryset = Transaction.objects.filter(user=self.request.user)
        return queryset
