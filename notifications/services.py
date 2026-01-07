"""
Email notification services for sending order and payment confirmations
"""
import logging
from django.conf import settings
from .utils import EmailService

logger = logging.getLogger(__name__)


def send_welcome_email(user) -> bool:
    """
    Send welcome email to newly registered user.
    
    Args:
        user: User instance (newly created)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not user.email:
            logger.warning(f"User {user.id} has no email, skipping welcome email")
            return False
        
        # Prepare email context
        recipient_name = user.get_full_name() or user.first_name or user.username or user.email.split('@')[0]
        
        context = {
            'recipient_name': recipient_name,
        }
        
        # Render email template
        try:
            message = EmailService.render_template('emails/welcome.txt', context)
        except Exception as e:
            logger.error(f"Failed to render welcome email template: {e}")
            # Fallback to simple message
            message = f"""Welcome to Bank Pro!

Hello {recipient_name},

Thank you for creating an account with Bank Pro! We're excited to have you on board.

Your account has been successfully created and you can now browse our catalog, add funds to your wallet, and make purchases.

If you have any questions, please contact @mentor_kev on Telegram.

Welcome aboard!

Best regards,
The Bank Pro Team"""
        
        # Send email
        subject = "Welcome to Bank Pro!"
        success = EmailService.send_email(subject, message, user.email)
        
        # Log notification
        EmailService.log_email_notification(
            user=user,
            email_type='welcome',
            status='sent' if success else 'failed',
            recipient_email=user.email,
            order=None,
            error_message=None if success else "Email sending failed"
        )
        
        if success:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.error(f"Failed to send welcome email to {user.email}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to user {user.id}: {e}", exc_info=True)
        # Log failed notification
        try:
            EmailService.log_email_notification(
                user=user,
                email_type='welcome',
                status='failed',
                recipient_email=user.email,
                order=None,
                error_message=str(e)
            )
        except:
            pass
        return False


def send_deposit_confirmation_email(user, amount: float, network_name: str, tx_hash: str, new_balance: float) -> bool:
    """
    Send deposit confirmation email to user when deposit is credited to wallet.
    
    Args:
        user: User instance
        amount: Deposit amount in USD
        network_name: Name of the crypto network (e.g., 'Bitcoin', 'Ethereum')
        tx_hash: Transaction hash
        new_balance: New wallet balance after deposit
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not user.email:
            logger.warning(f"User {user.id} has no email, skipping deposit confirmation")
            return False
        
        # Prepare email context
        recipient_name = user.get_full_name() or user.first_name or user.username or user.email.split('@')[0]
        
        context = {
            'recipient_name': recipient_name,
            'amount': f"{amount:.2f}",
            'network_name': network_name,
            'tx_hash': tx_hash,
            'new_balance': f"{new_balance:.2f}",
        }
        
        # Render email template
        try:
            message = EmailService.render_template('emails/deposit_confirmation.txt', context)
        except Exception as e:
            logger.error(f"Failed to render deposit confirmation template: {e}")
            # Fallback to simple message
            message = f"""Deposit Confirmed - ${amount:.2f} Added to Your Wallet

Hello {recipient_name},

Your deposit has been successfully processed and credited to your wallet.

Deposit Details:
- Amount: ${amount:.2f} USD
- Network: {network_name}
- Transaction Hash: {tx_hash}
- New Wallet Balance: ${new_balance:.2f} USD

Your wallet balance has been updated. You can now use these funds to make purchases.

If you have any questions, please contact @mentor_kev on Telegram.

Thank you for your deposit!"""
        
        # Send email
        subject = f"Deposit Confirmed - ${amount:.2f} Added to Your Wallet"
        success = EmailService.send_email(subject, message, user.email)
        
        # Log notification
        EmailService.log_email_notification(
            user=user,
            email_type='deposit_confirmation',
            status='sent' if success else 'failed',
            recipient_email=user.email,
            order=None,
            error_message=None if success else "Email sending failed"
        )
        
        if success:
            logger.info(f"Deposit confirmation email sent to {user.email} for ${amount:.2f} deposit")
        else:
            logger.error(f"Failed to send deposit confirmation email to {user.email}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send deposit confirmation email to user {user.id}: {e}", exc_info=True)
        # Log failed notification
        try:
            EmailService.log_email_notification(
                user=user,
                email_type='deposit_confirmation',
                status='failed',
                recipient_email=user.email,
                order=None,
                error_message=str(e)
            )
        except:
            pass
        return False


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
            item_price = item.unit_price_minor.amount  # MoneyField stores dollars
            items_list.append(f"{item.quantity}x {item_name} - ${item_price:.2f}")
        
        items_text = "\n".join(items_list) if items_list else "No items"
        
        # Prepare template context
        context = {
            'order_number': order.order_number,
            'order_date': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'items_list': items_text,
            'total': f"{order.total_minor.amount:.2f}",  # MoneyField stores dollars
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

Total: ${order.total_minor.amount:.2f}

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

