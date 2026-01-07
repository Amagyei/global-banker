"""
URL configuration for wallet API v2 (OXA Pay integration)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_v2 import (
    WalletV2ViewSet,
    CryptoNetworkV2ViewSet,
    TopUpIntentV2ViewSet,
    OxaPayPaymentViewSet,
    OxaPayStaticAddressViewSet,
    OxaPayInvoiceViewSet,
    AddressValidationViewSet,
    FeeEstimationViewSet,
)
from .webhooks import oxapay_webhook
from .webhook_views import webhook_status, webhook_payment_detail, test_webhook

router = DefaultRouter()
router.register(r'wallet', WalletV2ViewSet, basename='wallet-v2')
router.register(r'networks', CryptoNetworkV2ViewSet, basename='networks-v2')
router.register(r'topups', TopUpIntentV2ViewSet, basename='topup-v2')
router.register(r'payments', OxaPayPaymentViewSet, basename='payment')
router.register(r'static-addresses', OxaPayStaticAddressViewSet, basename='static-address')
router.register(r'invoices', OxaPayInvoiceViewSet, basename='invoice')
router.register(r'address', AddressValidationViewSet, basename='address-validation')
router.register(r'fees', FeeEstimationViewSet, basename='fee-estimation')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/', oxapay_webhook, name='webhook'),
    # Webhook monitoring endpoints (admin only)
    path('webhook/status/', webhook_status, name='webhook-status'),
    path('webhook/payment/<str:track_id>/', webhook_payment_detail, name='webhook-payment-detail'),
    path('webhook/test/', test_webhook, name='webhook-test'),
]

