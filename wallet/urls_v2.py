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
)
from .webhooks import oxapay_webhook
from .webhook_views import webhook_status, webhook_payment_detail, test_webhook

router = DefaultRouter()
router.register(r'wallet', WalletV2ViewSet, basename='wallet-v2')
router.register(r'networks', CryptoNetworkV2ViewSet, basename='networks-v2')
router.register(r'topups', TopUpIntentV2ViewSet, basename='topup-v2')
router.register(r'oxapay/payments', OxaPayPaymentViewSet, basename='oxapay-payment')
router.register(r'oxapay/static-addresses', OxaPayStaticAddressViewSet, basename='oxapay-static-address')
router.register(r'oxapay/invoices', OxaPayInvoiceViewSet, basename='oxapay-invoice')

urlpatterns = [
    path('', include(router.urls)),
    path('oxapay/webhook/', oxapay_webhook, name='oxapay-webhook'),
    # Webhook monitoring endpoints (admin only)
    path('oxapay/webhook/status/', webhook_status, name='webhook-status'),
    path('oxapay/webhook/payment/<str:track_id>/', webhook_payment_detail, name='webhook-payment-detail'),
    path('oxapay/webhook/test/', test_webhook, name='webhook-test'),
]

