#!/usr/bin/env python
"""
Test Brevo email sending through the notification system.
This simulates sending an order confirmation email.
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.services import send_order_confirmation_email
from notifications.utils import EmailService
from orders.models import Order, OrderItem
from catalog.models import Account

User = get_user_model()

def test_notification_email():
    """Test sending email through notification system"""
    print("=" * 60)
    print("Testing Brevo Email via Notification System")
    print("=" * 60)
    
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("\n⚠️  No TEST_EMAIL environment variable set.")
        print("   Usage: TEST_EMAIL=your@email.com python test_brevo_notification.py")
        return False
    
    print(f"\n📬 Test Email: {test_email}\n")
    
    # Test 1: Direct EmailService
    print("Test 1: EmailService.send_email()...")
    try:
        success = EmailService.send_email(
            subject='✅ Brevo Test - EmailService',
            message='This is a test email sent through EmailService utility.\n\nThis verifies the notification system can send emails via Brevo.',
            recipient_email=test_email,
        )
        if success:
            print("   ✅ Email sent successfully!")
        else:
            print("   ❌ EmailService.send_email returned False")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Template rendering
    print("\nTest 2: Template rendering...")
    try:
        context = {
            'order_number': 'TEST-ORDER-001',
            'order_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'items': [
                {'quantity': 1, 'name': 'Test Account', 'price': '$100.00'},
            ],
            'total': '$100.00',
            'recipient_name': 'Test User',
            'support_contact': '@mentor_kev on Telegram',
        }
        message = EmailService.render_template('emails/order_confirmation.txt', context)
        print("   ✅ Template rendered successfully")
        print(f"   📄 Message length: {len(message)} characters")
    except Exception as e:
        print(f"   ❌ Error rendering template: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Send email with template
    print("\nTest 3: Send email with rendered template...")
    try:
        success = EmailService.send_email(
            subject='✅ Brevo Test - Order Confirmation Template',
            message=message,
            recipient_email=test_email,
        )
        if success:
            print("   ✅ Email with template sent successfully!")
        else:
            print("   ❌ Failed to send email with template")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All notification tests passed!")
    print("📧 Please check your inbox (and spam folder) for test emails.")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_notification_email()
    sys.exit(0 if success else 1)

