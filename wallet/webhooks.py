"""
Webhook handlers for OXA Pay payment callbacks
"""
import logging
import json
import hmac
import hashlib
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction as db_transaction
# Email sending moved to notifications/services.py
from django.conf import settings

logger = logging.getLogger(__name__)

from .models import OxaPayPayment, OxaPayStaticAddress, Wallet, TopUpIntent
from .oxa_pay_client import OxaPayClient
from transactions.models import Transaction


@csrf_exempt
@require_http_methods(["POST"])
def oxapay_webhook(request):
    """
    Handle OXA Pay webhook callbacks for payment notifications.
    
    According to OXA Pay docs:
    - Uses HMAC-SHA512 with MERCHANT_API_KEY as secret
    - Signature is in "HMAC" header (not X-OxaPay-Signature)
    - Status values: "Paying", "Paid", "Failed", "Expired"
    - Must return HTTP 200 with content "OK" (exact string)
    - Payload contains "txs" array with transaction details
    
    Expected payload structure (from OXA Pay):
    {
        "track_id": "string",
        "status": "Paying" | "Paid" | "Failed" | "Expired",
        "type": "invoice" | "white_label" | "static_address" | "payment_link" | "donation",
        "amount": decimal,
        "value": decimal,
        "sent_value": decimal,
        "currency": "POL",
        "order_id": "string",
        "email": "string",
        "txs": [{
            "status": "confirming" | "confirmed",
            "tx_hash": "string",
            "sent_amount": decimal,
            "received_amount": decimal,
            "currency": "POL",
            "network": "Polygon Network",
            "address": "string",
            "confirmations": integer,
            ...
        }],
        ...
    }
    """
    try:
        # Get raw body for signature verification (must be raw bytes/string)
        body = request.body.decode('utf-8')
        payload = json.loads(body)
        
        # Verify HMAC signature (OXA Pay uses HMAC-SHA512, header is "HMAC")
        hmac_header = request.headers.get('HMAC', '')
        if hmac_header:
            try:
                # Get API key from settings
                api_key = getattr(settings, 'OXAPAY_API_KEY', None)
                if not api_key:
                    # Try to get from OxaPayClient
                    oxa_client = OxaPayClient()
                    api_key = oxa_client.api_key
                
                if api_key:
                    # Calculate HMAC-SHA512 signature
                    calculated_hmac = hmac.new(
                        api_key.encode('utf-8'),
                        body.encode('utf-8'),
                        hashlib.sha512
                    ).hexdigest()
                    
                    if not hmac.compare_digest(calculated_hmac, hmac_header):
                        logger.warning(f"Invalid HMAC signature for track_id: {payload.get('track_id')}")
                        return HttpResponseBadRequest("Invalid HMAC signature")
                    logger.debug(f"HMAC signature verified for track_id: {payload.get('track_id')}")
                else:
                    logger.warning("OXAPAY_API_KEY not found, skipping signature verification")
            except Exception as e:
                logger.error(f"HMAC signature verification failed: {e}", exc_info=True)
                # In production, you might want to reject invalid signatures
                # For now, we'll log and continue
        else:
            logger.warning("No HMAC header found in webhook request")
        
        track_id = payload.get('track_id')
        if not track_id:
            logger.error("Webhook missing track_id")
            return HttpResponseBadRequest("Missing track_id")
        
        # OXA Pay sends capitalized status: "Paying", "Paid", "Failed", "Expired"
        payment_status_raw = payload.get('status', '')
        payment_status = payment_status_raw.lower()  # Normalize to lowercase for our DB
        
        # Extract transaction hash from txs array if available
        tx_hash = None
        txs = payload.get('txs', [])
        if txs and len(txs) > 0:
            tx_hash = txs[0].get('tx_hash')
        
        # Find payment record
        payment = OxaPayPayment.objects.filter(track_id=track_id).first()
        if not payment:
            # Try static address
            static_address = OxaPayStaticAddress.objects.filter(track_id=track_id).first()
            if static_address:
                # Create payment record from static address
                payment = OxaPayPayment.objects.create(
                    user=static_address.user,
                    track_id=track_id,
                    network=static_address.network,
                    address=static_address.address,
                    amount=float(payload.get('amount', 0)),
                    pay_amount=float(payload.get('value', 0)) if payload.get('value') else None,
                    pay_currency=payload.get('currency', '').lower() if payload.get('currency') else 'btc',
                    currency=payload.get('currency', 'usd').lower(),
                    status='pending',
                    order_id=payload.get('order_id', ''),
                    email=static_address.email or payload.get('email', ''),
                    description=static_address.description or payload.get('description', ''),
                    raw_response=payload
                )
            else:
                logger.warning(f"Payment not found for track_id: {track_id}")
                # Still return OK to prevent OXA Pay from retrying
                return HttpResponse("OK", status=200)
        
        # Update payment status and transaction hash
        old_status = payment.status
        payment.status = payment_status
        if tx_hash:
            payment.tx_hash = tx_hash
        payment.raw_response = payload
        payment.updated_at = timezone.now()
        payment.save()
        
        logger.info(f"OXA Pay webhook: track_id={track_id}, status={payment_status_raw} (normalized: {payment_status})")
        
        # Process based on status
        if payment_status == 'paid' and old_status != 'paid':
            # Payment confirmed - credit user wallet
            process_paid_payment(payment, payload)
        elif payment_status == 'failed':
            # Payment failed - notify user
            process_failed_payment(payment, payload)
        elif payment_status == 'expired':
            # Payment expired - notify user
            process_expired_payment(payment, payload)
        elif payment_status == 'paying':
            # Payment sent but not confirmed yet - just log
            logger.info(f"Payment {track_id} is in 'Paying' status, waiting for confirmation")
        
        # OXA Pay requires exact "OK" response (not "ok" or "Ok")
        return HttpResponse("OK", status=200, content_type='text/plain')
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook payload: {e}")
        return HttpResponseBadRequest("Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        # Still return OK to prevent OXA Pay from retrying invalid requests
        return HttpResponse("OK", status=200, content_type='text/plain')


def process_paid_payment(payment: OxaPayPayment, payload: dict):
    """
    Process a paid OXA Pay payment: 
    - If linked to an order, mark order as paid and fulfill it
    - If it's a top-up, credit user wallet
    Also sends notification email to user.
    
    Args:
        payment: OxaPayPayment instance
        payload: Webhook payload from OXA Pay
    """
    try:
        with db_transaction.atomic():
            order_id = payment.order_id or payload.get('order_id', '')
            
            # Check if this is an order payment (order_id starts with "ORD-")
            if order_id and order_id.startswith('ORD-'):
                # This is an order payment - update order status
                from orders.models import Order, Cart
                try:
                    order = Order.objects.get(order_number=order_id, user=payment.user)
                    
                    if order.status != 'paid':
                        # Mark order as paid
                        order.status = 'paid'
                        order.save()
                        
                        # Send order confirmation email to ALL confirmed purchases
                        try:
                            from notifications.services import send_order_confirmation_email
                            send_order_confirmation_email(order)
                        except Exception as e:
                            logger.error(f"Failed to send order confirmation email for order {order.order_number}: {e}")
                        
                        # Clear cart (items were already moved to order)
                        cart, _ = Cart.objects.get_or_create(user=payment.user)
                        cart.items.all().delete()
                        
                        # Create transaction record for order payment
                        wallet, _ = Wallet.objects.get_or_create(
                            user=payment.user,
                            defaults={'currency_code': 'USD', 'balance_minor': 0}
                        )
                        
                        amount_minor = int(payment.amount * 100)
                        Transaction.objects.create(
                            user=payment.user,
                            direction='debit',
                            category='purchase',
                            amount_minor=amount_minor,
                            currency_code='USD',
                            description=f'Order {order.order_number} payment via OXA Pay',
                            balance_after_minor=wallet.balance_minor,
                            status='completed',
                            related_order_id=order.id,
                        )
                        
                        logger.info(
                            f"✅ Order {order.order_number} marked as paid via OXA Pay payment {payment.track_id}"
                        )
                    else:
                        logger.info(f"Order {order.order_number} already marked as paid")
                        
                except Order.DoesNotExist:
                    logger.warning(f"Order {order_id} not found for payment {payment.track_id}")
                    # Fall through to top-up processing
                except Exception as e:
                    logger.error(f"Failed to process order payment: {e}", exc_info=True)
                    raise
            
            # If this is a top-up (has topup_intent) or no order found, credit wallet
            if payment.topup_intent or not (order_id and order_id.startswith('ORD-')):
                # Get or create user wallet
                wallet, _ = Wallet.objects.get_or_create(
                    user=payment.user,
                    defaults={'currency_code': 'USD', 'balance_minor': 0}
                )
                
                # Convert amount to minor units (cents)
                amount_minor = int(payment.amount * 100)
                
                # Check if already credited (prevent double crediting)
                existing_tx = Transaction.objects.filter(
                    user=payment.user,
                    related_topup_intent_id=payment.topup_intent.id if payment.topup_intent else None,
                    related_oxapay_payment_id=payment.id,
                    direction='credit',
                    category='topup',
                    status='completed'
                ).first()
                
                if existing_tx:
                    logger.info(f"Payment {payment.track_id} already credited, skipping duplicate")
                    return
                
                # Credit user wallet
                wallet.balance_minor += amount_minor
                wallet.save()
                
                # Update top-up intent if exists
                if payment.topup_intent:
                    payment.topup_intent.status = 'succeeded'
                    payment.topup_intent.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=payment.user,
                    direction='credit',
                    category='topup',
                    amount_minor=amount_minor,
                    currency_code='USD',
                    description=f'Crypto deposit via OXA Pay ({payment.pay_currency.upper()})',
                    balance_after_minor=wallet.balance_minor,
                    status='completed',
                    related_topup_intent_id=payment.topup_intent.id if payment.topup_intent else None,
                )
                
                logger.info(
                    f"✅ Credited ${amount_minor/100:.2f} to wallet for user {payment.user.email} "
                    f"via OXA Pay payment {payment.track_id}"
                )
            
            # Send success notification email (using centralized notifications service)
            try:
                from notifications.services import send_payment_confirmation_email
                send_payment_confirmation_email(
                    user=payment.user,
                    payment=payment,
                    status='success',
                    amount=payment.amount
                )
            except Exception as e:
                logger.error(f"Failed to send success notification email: {e}")
            
    except Exception as e:
        logger.error(f"Failed to process paid payment {payment.track_id}: {e}", exc_info=True)
        raise


def process_failed_payment(payment: OxaPayPayment, payload: dict):
    """
    Process a failed OXA Pay payment: notify user.
    
    Args:
        payment: OxaPayPayment instance
        payload: Webhook payload from OXA Pay
    """
    try:
        logger.warning(f"❌ Payment {payment.track_id} failed for user {payment.user.email}")
        
        # Update top-up intent if exists
        if payment.topup_intent:
            payment.topup_intent.status = 'failed'
            payment.topup_intent.save()
        
        # Send failure notification email (using centralized notifications service)
        try:
            from notifications.services import send_payment_confirmation_email
            send_payment_confirmation_email(
                user=payment.user,
                payment=payment,
                status='failed',
                amount=payment.amount
            )
        except Exception as e:
            logger.error(f"Failed to send failure notification email: {e}")
            
    except Exception as e:
        logger.error(f"Failed to process failed payment {payment.track_id}: {e}", exc_info=True)


def process_expired_payment(payment: OxaPayPayment, payload: dict):
    """
    Process an expired OXA Pay payment: notify user.
    
    Args:
        payment: OxaPayPayment instance
        payload: Webhook payload from OXA Pay
    """
    try:
        logger.info(f"⏰ Payment {payment.track_id} expired for user {payment.user.email}")
        
        # Update top-up intent if exists
        if payment.topup_intent:
            payment.topup_intent.status = 'expired'
            payment.topup_intent.save()
        
        # Send expiration notification email (using centralized notifications service)
        try:
            from notifications.services import send_payment_confirmation_email
            send_payment_confirmation_email(
                user=payment.user,
                payment=payment,
                status='expired',
                amount=payment.amount
            )
        except Exception as e:
            logger.error(f"Failed to send expiration notification email: {e}")
            
    except Exception as e:
        logger.error(f"Failed to process expired payment {payment.track_id}: {e}", exc_info=True)


# Note: send_payment_notification() has been moved to notifications/services.py
# as send_payment_confirmation_email() for centralized email management

