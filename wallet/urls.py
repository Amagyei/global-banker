from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WalletViewSet,
    CryptoNetworkViewSet,
    DepositAddressViewSet,
    TopUpIntentViewSet,
    OnChainTransactionViewSet,
)

router = DefaultRouter()
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'networks', CryptoNetworkViewSet, basename='network')
router.register(r'deposit-addresses', DepositAddressViewSet, basename='depositaddress')
router.register(r'topups', TopUpIntentViewSet, basename='topup')
router.register(r'transactions', OnChainTransactionViewSet, basename='onchaintransaction')

urlpatterns = [
    path('', include(router.urls)),
]

