#!/usr/bin/env python
"""
Test Brevo configuration and API connectivity.
This test verifies the API key is valid without sending an email.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from django.conf import settings
import requests

def test_brevo_api_connection():
    """Test Brevo API connection by checking account info"""
    print("=" * 60)
    print("Brevo Configuration & API Test")
    print("=" * 60)
    
    # Check configuration
    print(f"\n1. Email Backend: {settings.EMAIL_BACKEND}")
    if 'brevo' not in settings.EMAIL_BACKEND.lower():
        print("   ❌ Email backend is not set to Brevo!")
        return False
    print("   ✅ Email backend configured correctly")
    
    # Check API key
    brevo_api_key = settings.ANYMAIL.get('BREVO_API_KEY') if hasattr(settings, 'ANYMAIL') else None
    if not brevo_api_key:
        print("\n   ❌ BREVO_API_KEY is NOT set in settings!")
        return False
    
    masked_key = brevo_api_key[:8] + '...' + brevo_api_key[-4:] if len(brevo_api_key) > 12 else '***'
    print(f"\n2. BREVO_API_KEY: {masked_key}")
    print("   ✅ API key is configured")
    
    # Check from email
    from_email = settings.DEFAULT_FROM_EMAIL
    print(f"\n3. DEFAULT_FROM_EMAIL: {from_email}")
    if from_email == 'noreply@yourdomain.com':
        print("   ⚠️  WARNING: Using default email. Update this in settings.py")
    else:
        print("   ✅ From email is configured")
    
    # Test API connection
    print("\n4. Testing Brevo API connection...")
    try:
        # Brevo API endpoint to get account info (validates API key)
        url = "https://api.brevo.com/v3/account"
        headers = {
            "accept": "application/json",
            "api-key": brevo_api_key
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()
            print("   ✅ API connection successful!")
            print(f"   📧 Account Email: {account_data.get('email', 'N/A')}")
            print(f"   👤 Company: {account_data.get('companyName', 'N/A')}")
            plan_info = account_data.get('plan', [])
            if isinstance(plan_info, list) and len(plan_info) > 0:
                plan_type = plan_info[0].get('type', 'N/A') if isinstance(plan_info[0], dict) else 'N/A'
            elif isinstance(plan_info, dict):
                plan_type = plan_info.get('type', 'N/A')
            else:
                plan_type = 'N/A'
            print(f"   📊 Plan: {plan_type}")
            return True
        elif response.status_code == 401:
            print("   ❌ API key is invalid or unauthorized")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"   ⚠️  API returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Failed to connect to Brevo API: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_sending():
    """Test actual email sending if TEST_EMAIL is provided"""
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("\n" + "=" * 60)
        print("📧 Email Sending Test (Skipped)")
        print("=" * 60)
        print("\nTo test email sending, run:")
        print("  TEST_EMAIL=your@email.com python test_brevo_config.py")
        return True
    
    print("\n" + "=" * 60)
    print("📧 Email Sending Test")
    print("=" * 60)
    print(f"\nSending test email to: {test_email}")
    
    try:
        from django.core.mail import send_mail
        
        result = send_mail(
            subject='✅ Brevo Integration Test - Global Banker',
            message='This is a test email to verify Brevo integration.\n\nIf you receive this, everything is working correctly!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        if result:
            print("   ✅ Test email sent successfully!")
            print("   📬 Please check your inbox (and spam folder)")
            return True
        else:
            print("   ⚠️  send_mail returned False")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n🚀 Testing Brevo Email Integration\n")
    
    # Test API connection
    api_ok = test_brevo_api_connection()
    
    # Test email sending if email provided
    email_ok = test_email_sending()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"API Connection: {'✅' if api_ok else '❌'}")
    if os.environ.get('TEST_EMAIL'):
        print(f"Email Sending: {'✅' if email_ok else '❌'}")
    else:
        print("Email Sending: ⏭️  (skipped - no TEST_EMAIL)")
    
    if api_ok:
        print("\n🎉 Brevo API is properly configured and connected!")
        if not os.environ.get('TEST_EMAIL'):
            print("\n💡 To test email sending, run:")
            print("   TEST_EMAIL=your@email.com python test_brevo_config.py")
    else:
        print("\n⚠️  Configuration issues detected. Please check:")
        print("   1. BREVO_API_KEY is correct in .env file")
        print("   2. API key has proper permissions in Brevo dashboard")
    
    return api_ok


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

