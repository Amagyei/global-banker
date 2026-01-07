#!/usr/bin/env python
"""
Simple non-interactive test for Brevo email integration.
Usage: TEST_EMAIL=your@email.com python test_brevo_simple.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from notifications.utils import EmailService

def main():
    """Run Brevo email test"""
    print("=" * 60)
    print("Brevo Email Integration Test")
    print("=" * 60)
    
    # Check configuration
    print(f"\n📧 Email Backend: {settings.EMAIL_BACKEND}")
    
    brevo_api_key = settings.ANYMAIL.get('BREVO_API_KEY') if hasattr(settings, 'ANYMAIL') else None
    if brevo_api_key:
        masked_key = brevo_api_key[:8] + '...' + brevo_api_key[-4:] if len(brevo_api_key) > 12 else '***'
        print(f"✅ BREVO_API_KEY: {masked_key}")
    else:
        print("❌ BREVO_API_KEY is NOT set!")
        return False
    
    print(f"📨 From Email: {settings.DEFAULT_FROM_EMAIL}")
    
    # Get test email
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("\n⚠️  No TEST_EMAIL environment variable set.")
        print("   Set it with: export TEST_EMAIL=your@email.com")
        print("   Or run: TEST_EMAIL=your@email.com python test_brevo_simple.py")
        return False
    
    print(f"📬 Test Email: {test_email}\n")
    
    # Test 1: Direct send_mail
    print("Test 1: Direct send_mail()...")
    try:
        result = send_mail(
            subject='✅ Brevo Test - Global Banker',
            message='This is a test email from Global Banker using Brevo API.\n\nIf you receive this, Brevo integration is working correctly!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        if result:
            print("   ✅ Email sent successfully!")
        else:
            print("   ⚠️  send_mail returned False")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: EmailService
    print("\nTest 2: EmailService utility...")
    try:
        success = EmailService.send_email(
            subject='✅ Brevo Test via EmailService - Global Banker',
            message='This is a test email sent through EmailService utility.\n\nThis verifies the notification system can send emails via Brevo.',
            recipient_email=test_email,
        )
        if success:
            print("   ✅ Email sent successfully via EmailService!")
        else:
            print("   ⚠️  EmailService.send_email returned False")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! Brevo integration is working.")
    print("📧 Please check your inbox (and spam folder) for test emails.")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

