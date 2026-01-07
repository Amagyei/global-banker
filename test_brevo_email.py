#!/usr/bin/env python
"""
Test script for Brevo email integration.
Run this to verify that Brevo email sending is working correctly.
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

def test_brevo_configuration():
    """Test that Brevo is properly configured"""
    print("=" * 60)
    print("Testing Brevo Email Configuration")
    print("=" * 60)
    
    # Check email backend
    print(f"\n1. Email Backend: {settings.EMAIL_BACKEND}")
    if 'brevo' not in settings.EMAIL_BACKEND.lower():
        print("   ⚠️  WARNING: Email backend is not set to Brevo!")
    else:
        print("   ✅ Email backend is set to Brevo")
    
    # Check API key
    brevo_api_key = settings.ANYMAIL.get('BREVO_API_KEY') if hasattr(settings, 'ANYMAIL') else None
    if brevo_api_key:
        print(f"   ✅ BREVO_API_KEY is set (length: {len(brevo_api_key)} chars)")
    else:
        print("   ❌ BREVO_API_KEY is NOT set!")
        return False
    
    # Check default from email
    default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
    print(f"\n2. Default From Email: {default_from}")
    if not default_from or default_from == 'noreply@yourdomain.com':
        print("   ⚠️  WARNING: DEFAULT_FROM_EMAIL should be changed from default!")
    else:
        print("   ✅ DEFAULT_FROM_EMAIL is configured")
    
    return True


def test_send_email_direct():
    """Test sending email directly using Django's send_mail"""
    print("\n" + "=" * 60)
    print("Test 1: Direct Email Send (Django send_mail)")
    print("=" * 60)
    
    # Get test email from user or use a default
    test_email = os.environ.get('TEST_EMAIL', '')
    if not test_email:
        test_email = input("\nEnter test email address (or press Enter to skip): ").strip()
    
    if not test_email:
        print("   ⏭️  Skipping direct email test (no email provided)")
        return True
    
    try:
        result = send_mail(
            subject='Test Email from Global Banker - Brevo Integration',
            message='This is a test email to verify Brevo email integration is working correctly.\n\nIf you receive this email, the Brevo API is properly configured!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        if result:
            print(f"   ✅ Email sent successfully to {test_email}!")
            print("   📧 Please check your inbox (and spam folder)")
            return True
        else:
            print(f"   ❌ Email sending returned False (no error, but email not sent)")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def test_email_service():
    """Test sending email using EmailService utility"""
    print("\n" + "=" * 60)
    print("Test 2: Email Service Utility")
    print("=" * 60)
    
    test_email = os.environ.get('TEST_EMAIL', '')
    if not test_email:
        test_email = input("\nEnter test email address (or press Enter to skip): ").strip()
    
    if not test_email:
        print("   ⏭️  Skipping EmailService test (no email provided)")
        return True
    
    try:
        success = EmailService.send_email(
            subject='Test Email via EmailService - Brevo Integration',
            message='This is a test email sent through the EmailService utility class.\n\nThis verifies that the notification system can send emails via Brevo.',
            recipient_email=test_email,
        )
        
        if success:
            print(f"   ✅ Email sent successfully via EmailService to {test_email}!")
            print("   📧 Please check your inbox (and spam folder)")
            return True
        else:
            print(f"   ❌ EmailService.send_email returned False")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to send email via EmailService: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n🚀 Starting Brevo Email Integration Tests\n")
    
    # Test configuration
    if not test_brevo_configuration():
        print("\n❌ Configuration test failed. Please check your settings.")
        return
    
    # Test direct email
    test1_result = test_send_email_direct()
    
    # Test EmailService
    test2_result = test_email_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Configuration: ✅")
    print(f"Direct Email Send: {'✅' if test1_result else '❌'}")
    print(f"EmailService Utility: {'✅' if test2_result else '❌'}")
    
    if test1_result or test2_result:
        print("\n🎉 At least one email test passed! Brevo integration is working.")
    else:
        print("\n⚠️  Email tests failed. Please check:")
        print("   1. BREVO_API_KEY is set correctly in .env")
        print("   2. DEFAULT_FROM_EMAIL is a verified sender in Brevo")
        print("   3. django-anymail is installed: pip install django-anymail")
        print("   4. Check Brevo dashboard for any errors")


if __name__ == '__main__':
    main()

