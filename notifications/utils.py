"""
Email utility functions for rendering templates and sending emails
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class EmailService:
    """Utility class for email operations"""
    
    @staticmethod
    def send_email(subject: str, message: str, recipient_email: str, from_email: str = None) -> bool:
        """
        Send email using Django's send_mail.
        
        Args:
            subject: Email subject
            message: Email message body (plain text)
            recipient_email: Recipient email address
            from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not recipient_email:
            logger.warning("No recipient email provided, skipping email send")
            return False
        
        if not hasattr(settings, 'EMAIL_BACKEND') or not settings.EMAIL_BACKEND:
            logger.debug(f"Email backend not configured, skipping email to {recipient_email}")
            return False
        
        try:
            from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
            
            send_mail(
                subject=subject,
                message=message.strip(),
                from_email=from_email,
                recipient_list=[recipient_email],
                fail_silently=True,
            )
            logger.info(f"Email sent successfully to {recipient_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def render_template(template_name: str, context: dict) -> str:
        """
        Render email template with context.
        
        Args:
            template_name: Template name (e.g., 'emails/order_confirmation.txt')
            context: Template context dictionary
            
        Returns:
            str: Rendered template content
        """
        try:
            return render_to_string(template_name, context).strip()
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def log_email_notification(user, email_type: str, status: str, recipient_email: str, order=None, error_message: str = None):
        """
        Log email notification to database (optional tracking).
        
        Args:
            user: User instance
            email_type: Type of email (e.g., 'order_confirmation')
            status: Status ('sent', 'failed', 'bounced')
            recipient_email: Email address
            order: Order instance (optional)
            error_message: Error message if failed (optional)
        """
        try:
            from .models import EmailNotification
            EmailNotification.objects.create(
                user=user,
                order=order,
                email_type=email_type,
                status=status,
                recipient_email=recipient_email,
                error_message=error_message,
            )
        except Exception as e:
            logger.warning(f"Failed to log email notification: {e}")




