"""
Email notification services for sending order and payment confirmations
"""
import logging
from django.conf import settings
from .utils import EmailService

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order) -> bool:
    """
    Send order confirmation email to user.
    
    CRITICAL: This function MUST be called for ALL confirmed purchases
    (orders with status='paid').
    
    Args:
        order: Order instance (must have status='paid')
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if order.status != 'paid':
            logger.warning(f"Order {order.order_number} is not paid (status: {order.status}), skipping email")
            return False
        
        user = order.user
        if not user.email:
            logger.warning(f"User {user.id} has no email, skipping order confirmation")
            return False
        
        # Prepare email context
        recipient_name = order.recipient.get('name', user.email.split('@')[0])
        recipient_email = order.recipient.get('email', user.email)
        
        # Build items list
        items_list = []
        for item in order.items.all():
            # Get item name from account or fullz_package (same logic as serializer)
            if item.account:
                item_name = item.account.name
            elif item.fullz_package:
                item_name = item.fullz_package.name
            else:
                item_name = 'Unknown Item'
            item_price = item.unit_price_minor / 100
            items_list.append(f"{item.quantity}x {item_name} - ${item_price:.2f}")
        
        items_text = "\n".join(items_list) if items_list else "No items"
        
        # Prepare template context
        context = {
            'order_number': order.order_number,
            'order_date': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'items_list': items_text,
            'total': f"{order.total_minor / 100:.2f}",  # Format with 2 decimal places
            'recipient_name': recipient_name,
        }
        
        # Render email template
        try:
            message = EmailService.render_template('emails/order_confirmation.txt', context)
        except Exception as e:
            logger.error(f"Failed to render order confirmation template: {e}")
            # Fallback to simple message
            message = f"""Thank you for your purchase!

Order Number: {order.order_number}
Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}

Items:
{items_text}

Total: ${order.total_minor / 100:.2f}

If you have any questions, please contact @mentor_kev on Telegram."""
        
        # Send email
        subject = f"Order Confirmation - {order.order_number}"
        success = EmailService.send_email(subject, message, recipient_email)
        
        # Log notification
        EmailService.log_email_notification(
            user=user,
            email_type='order_confirmation',
            status='sent' if success else 'failed',
            recipient_email=recipient_email,
            order=order,
            error_message=None if success else "Email sending failed"
        )
        
        if success:
            logger.info(f"Order confirmation email sent for order {order.order_number} to {recipient_email}")
        else:
            logger.error(f"Failed to send order confirmation email for order {order.order_number}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send order confirmation email for order {order.order_number}: {e}", exc_info=True)
        # Log failed notification
        try:
            EmailService.log_email_notification(
                user=order.user,
                email_type='order_confirmation',
                status='failed',
                recipient_email=order.user.email,
                order=order,
                error_message=str(e)
            )
        except:
            pass
        return False


def send_payment_confirmation_email(user, payment, status: str, amount: float) -> bool:
    """
    Send payment confirmation email to user.
    Moved from wallet/webhooks.py for centralized email management.
    
    Args:
        user: User instance
        payment: OxaPayPayment instance
        status: 'success', 'failed', or 'expired'
        amount: Payment amount
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not user.email:
            logger.warning(f"User {user.id} has no email, skipping payment notification")
            return False
        
        # Prepare email context
        # Get tx_hash from payment (may not exist on OxaPayPayment, check if attribute exists)
        tx_hash = getattr(payment, 'tx_hash', None) or 'N/A'
        
        context = {
            'amount': f"{amount:.2f}",  # Format with 2 decimal places
            'track_id': payment.track_id,
            'currency': payment.pay_currency.upper() if payment.pay_currency else 'USD',
            'tx_hash': tx_hash,
            'status': status,
        }
        
        # Subject and message based on status
        subject_map = {
            'success': f'Payment Confirmed - ${amount:.2f} Added to Your Wallet',
            'failed': f'Payment Failed - ${amount:.2f}',
            'expired': f'Payment Expired - ${amount:.2f}',
        }
        
        # Try to render template, fallback to simple message
        try:
            message = EmailService.render_template('emails/payment_confirmation.txt', context)
        except Exception as e:
            logger.warning(f"Failed to render payment confirmation template: {e}, using fallback")
            # Fallback message
            tx_hash = getattr(payment, 'tx_hash', None) or 'N/A'
            if status == 'success':
                message = f"""Your payment of ${amount:.2f} USD has been confirmed and credited to your wallet.

Payment Details:
- Track ID: {payment.track_id}
- Amount: ${amount:.2f} USD
- Currency: {payment.pay_currency.upper() if payment.pay_currency else 'USD'}
- Transaction Hash: {tx_hash}

Your wallet balance has been updated. Thank you for your payment!"""
            elif status == 'failed':
                message = f"""Your payment of ${amount:.2f} USD has failed.

Payment Details:
- Track ID: {payment.track_id}
- Amount: ${amount:.2f} USD
- Currency: {payment.pay_currency.upper() if payment.pay_currency else 'USD'}

Please try again or contact support if you continue to experience issues."""
            else:  # expired
                message = f"""Your payment of ${amount:.2f} USD has expired.

Payment Details:
- Track ID: {payment.track_id}
- Amount: ${amount:.2f} USD
- Currency: {payment.pay_currency.upper() if payment.pay_currency else 'USD'}

Please create a new payment to complete your top-up."""
        
        subject = subject_map.get(status, 'Payment Status Update')
        success = EmailService.send_email(subject, message, user.email)
        
        # Log notification
        EmailService.log_email_notification(
            user=user,
            email_type='payment_confirmation',
            status='sent' if success else 'failed',
            recipient_email=user.email,
            order=None,
            error_message=None if success else "Email sending failed"
        )
        
        if success:
            logger.info(f"Sent {status} payment notification email to {user.email}")
        else:
            logger.error(f"Failed to send {status} payment notification email to {user.email}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send payment notification: {e}", exc_info=True)
        # Log failed notification
        try:
            EmailService.log_email_notification(
                user=user,
                email_type='payment_confirmation',
                status='failed',
                recipient_email=user.email,
                order=None,
                error_message=str(e)
            )
        except:
            pass
        return False

