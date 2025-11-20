"""
Views for webhook monitoring and testing
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
import json

from .models import OxaPayPayment, OxaPayStaticAddress
from .webhooks import oxapay_webhook
from django.http import HttpRequest, HttpResponse


@api_view(['GET'])
@permission_classes([IsAdminUser])
def webhook_status(request):
    """
    Get webhook endpoint status and recent activity
    Admin only - shows webhook health and recent payments
    """
    try:
        # Get recent payments (last 24 hours)
        recent_payments = OxaPayPayment.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).order_by('-created_at')[:50]
        
        # Count by status
        status_counts = {}
        for status_choice in ['pending', 'paid', 'failed', 'expired']:
            status_counts[status_choice] = OxaPayPayment.objects.filter(
                status=status_choice,
                created_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()
        
        # Get pending payments (waiting for webhook)
        pending_payments = OxaPayPayment.objects.filter(
            status='pending',
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).order_by('-created_at')[:20]
        
        # Get recent successful payments
        paid_payments = OxaPayPayment.objects.filter(
            status='paid',
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).order_by('-created_at')[:20]
        
        # Check for expired payments
        expired_payments = OxaPayPayment.objects.filter(
            status='pending',
            expired_at__lt=timezone.now()
        ).count()
        
        return Response({
            'webhook_endpoint': '/api/v2/wallet/webhook/',
            'status': 'active',
            'last_24_hours': {
                'total_payments': recent_payments.count(),
                'status_breakdown': status_counts,
                'expired_but_pending': expired_payments,
            },
            'recent_pending': [
                {
                    'track_id': p.track_id,
                    'address': p.address,
                    'amount': str(p.amount),
                    'currency': p.currency.upper(),
                    'pay_currency': p.pay_currency.upper(),
                    'created_at': p.created_at.isoformat(),
                    'expired_at': p.expired_at.isoformat() if p.expired_at else None,
                    'is_expired': p.expired_at and timezone.now() > p.expired_at,
                    'user': p.user.email,
                }
                for p in pending_payments
            ],
            'recent_paid': [
                {
                    'track_id': p.track_id,
                    'address': p.address,
                    'amount': str(p.amount),
                    'currency': p.currency.upper(),
                    'pay_currency': p.pay_currency.upper(),
                    'paid_at': p.updated_at.isoformat(),
                    'user': p.user.email,
                }
                for p in paid_payments
            ],
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def webhook_payment_detail(request, track_id):
    """
    Get detailed information about a specific payment by track_id
    Admin only
    """
    try:
        payment = OxaPayPayment.objects.filter(track_id=track_id).first()
        
        if not payment:
            return Response(
                {'error': f'Payment with track_id {track_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if expired
        is_expired = payment.expired_at and timezone.now() > payment.expired_at
        
        return Response({
            'track_id': payment.track_id,
            'address': payment.address,
            'status': payment.status,
            'amount': str(payment.amount),
            'pay_amount': str(payment.pay_amount) if payment.pay_amount else None,
            'currency': payment.currency.upper(),
            'pay_currency': payment.pay_currency.upper(),
            'network': payment.network.name,
            'user': payment.user.email,
            'created_at': payment.created_at.isoformat(),
            'updated_at': payment.updated_at.isoformat(),
            'expired_at': payment.expired_at.isoformat() if payment.expired_at else None,
            'is_expired': is_expired,
            'callback_url': payment.callback_url,
            'order_id': payment.order_id,
            'description': payment.description,
            'topup_intent_id': str(payment.topup_intent.id) if payment.topup_intent else None,
            'raw_response': payment.raw_response,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def test_webhook(request):
    """
    Test webhook endpoint with sample payload
    Admin only - for testing webhook processing
    """
    try:
        # Get track_id from request
        track_id = request.data.get('track_id')
        
        if not track_id:
            return Response(
                {'error': 'track_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find payment
        payment = OxaPayPayment.objects.filter(track_id=track_id).first()
        
        if not payment:
            return Response(
                {'error': f'Payment with track_id {track_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create sample webhook payload
        sample_payload = {
            'track_id': track_id,
            'status': request.data.get('status', 'paid'),  # 'paid', 'failed', 'expired', 'paying'
            'type': 'white_label',
            'amount': float(payment.amount),
            'value': float(payment.pay_amount) if payment.pay_amount else float(payment.amount),
            'sent_value': float(payment.pay_amount) if payment.pay_amount else float(payment.amount),
            'currency': payment.pay_currency.upper(),
            'order_id': payment.order_id,
            'email': payment.email,
            'description': payment.description,
            'txs': [
                {
                    'status': 'confirmed',
                    'tx_hash': request.data.get('tx_hash', 'test_tx_hash_12345'),
                    'sent_amount': float(payment.pay_amount) if payment.pay_amount else float(payment.amount),
                    'received_amount': float(payment.pay_amount) if payment.pay_amount else float(payment.amount),
                    'currency': payment.pay_currency.upper(),
                    'network': payment.network.name,
                    'address': payment.address,
                    'confirmations': 10,
                }
            ] if request.data.get('status') == 'paid' else [],
        }
        
        # Create a mock request object
        from django.test import RequestFactory
        factory = RequestFactory()
        mock_request = factory.post(
            '/api/v2/wallet/webhook/',
            data=json.dumps(sample_payload),
            content_type='application/json',
            HTTP_HMAC='test_signature'  # Will fail verification but that's OK for testing
        )
        
        # Call webhook handler
        response = oxapay_webhook(mock_request)
        
        # Refresh payment from DB
        payment.refresh_from_db()
        
        return Response({
            'message': 'Webhook test completed',
            'original_status': payment._state.adding or 'unknown',
            'new_status': payment.status,
            'webhook_response_status': response.status_code,
            'webhook_response_content': response.content.decode('utf-8'),
            'test_payload': sample_payload,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

