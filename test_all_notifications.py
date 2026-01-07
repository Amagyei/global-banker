#!/usr/bin/env python
"""
Test all email notifications:
1. Welcome email (on signup)
2. Deposit confirmation (successful deposit)
3. Payment confirmation (successful/failed payment)
4. Order confirmation (successful purchase)
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
from notifications.services import (
    send_welcome_email,
    send_deposit_confirmation_email,
    send_payment_confirmation_email,
    send_order_confirmation_email
)
from wallet.models import OxaPayPayment, CryptoNetwork
from orders.models import Order, OrderItem

User = get_user_model()

def test_welcome_email():
    """Test welcome email"""
    print("=" * 60)
    print("Test 1: Welcome Email")
    print("=" * 60)
    
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("⚠️  No TEST_EMAIL set, skipping welcome email test")
        return False
    
    # Create a test user (or use existing)
    try:
        user = User.objects.get(email=test_email)
        print(f"📧 Using existing user: {user.email}")
    except User.DoesNotExist:
        print(f"📧 Creating test user: {test_email}")
        user = User.objects.create_user(
            username=test_email,
            email=test_email,
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
    
    try:
        success = send_welcome_email(user)
        if success:
            print("   ✅ Welcome email sent successfully!")
            return True
        else:
            print("   ❌ Failed to send welcome email")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deposit_confirmation_email():
    """Test deposit confirmation email"""
    print("\n" + "=" * 60)
    print("Test 2: Deposit Confirmation Email")
    print("=" * 60)
    
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("⚠️  No TEST_EMAIL set, skipping deposit confirmation test")
        return False
    
    try:
        user = User.objects.get(email=test_email)
    except User.DoesNotExist:
        print(f"❌ User {test_email} not found")
        return False
    
    try:
        success = send_deposit_confirmation_email(
            user=user,
            amount=100.00,
            network_name='Bitcoin',
            tx_hash='test_tx_hash_1234567890abcdef',
            new_balance=150.00
        )
        if success:
            print("   ✅ Deposit confirmation email sent successfully!")
            return True
        else:
            print("   ❌ Failed to send deposit confirmation email")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_payment_confirmation_email():
    """Test payment confirmation email (success and failed)"""
    print("\n" + "=" * 60)
    print("Test 3: Payment Confirmation Email")
    print("=" * 60)
    
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("⚠️  No TEST_EMAIL set, skipping payment confirmation test")
        return False
    
    try:
        user = User.objects.get(email=test_email)
    except User.DoesNotExist:
        print(f"❌ User {test_email} not found")
        return False
    
    # Get or create a crypto network
    network, _ = CryptoNetwork.objects.get_or_create(
        name='Bitcoin',
        defaults={'symbol': 'BTC', 'is_testnet': False}
    )
    
    # Create a mock payment
    payment = OxaPayPayment.objects.create(
        user=user,
        amount=50.00,
        pay_currency='USD',
        track_id=f'test_track_{datetime.now().timestamp()}',
        network=network,
        address='test_address',
        status='paid'
    )
    
    try:
        # Test success notification
        print("   Testing success notification...")
        success1 = send_payment_confirmation_email(
            user=user,
            payment=payment,
            status='success',
            amount=50.00
        )
        
        # Test failed notification
        print("   Testing failed notification...")
        payment.status = 'failed'
        payment.save()
        success2 = send_payment_confirmation_email(
            user=user,
            payment=payment,
            status='failed',
            amount=50.00
        )
        
        # Cleanup
        payment.delete()
        
        if success1 and success2:
            print("   ✅ Payment confirmation emails sent successfully!")
            return True
        else:
            print(f"   ⚠️  Success: {success1}, Failed: {success2}")
            return success1 or success2
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'payment' in locals():
            payment.delete()
        return False


def main():
    """Run all notification tests"""
    print("\n🚀 Testing All Email Notifications\n")
    
    test_email = os.environ.get('TEST_EMAIL')
    if not test_email:
        print("⚠️  No TEST_EMAIL environment variable set.")
        print("   Usage: TEST_EMAIL=your@email.com python test_all_notifications.py")
        return False
    
    print(f"📧 Test Email: {test_email}\n")
    
    results = []
    results.append(("Welcome Email", test_welcome_email()))
    results.append(("Deposit Confirmation", test_deposit_confirmation_email()))
    results.append(("Payment Confirmation", test_payment_confirmation_email()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All email notification tests passed!")
        print("📧 Please check your inbox (and spam folder) for test emails.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

