#!/usr/bin/env python3
"""
Quick test script for top-up validation system
Run: python test_topup_validation.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from django.contrib.auth import get_user_model
from wallet.models import CryptoNetwork, TopUpIntent, OxaPayPayment, Wallet
from wallet.views_v2 import TopUpIntentV2ViewSet
from wallet.webhooks import oxapay_webhook
from rest_framework.test import APIRequestFactory
from rest_framework import status
import json
import hmac
import hashlib
from django.conf import settings

User = get_user_model()

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_network_validation():
    """Test network validation"""
    print_section("1. Network Validation")
    
    # Get active networks
    networks = CryptoNetwork.objects.filter(is_active=True, db_is_testnet=False)
    print(f"✅ Found {networks.count()} active mainnet networks")
    
    for network in networks[:5]:  # Show first 5
        print(f"   - {network.native_symbol}: {network.name}")
    
    return networks.first()

def test_topup_creation(user, network):
    """Test top-up creation"""
    print_section("2. Top-Up Creation")
    
    factory = APIRequestFactory()
    request = factory.post('/api/v2/wallet/topups/', {
        'amount_minor': 1000,
        'network_id': str(network.id),
        'use_static_address': False
    }, format='json')
    request.user = user
    
    viewset = TopUpIntentV2ViewSet()
    viewset.request = request
    
    try:
        response = viewset.create(request)
        if response.status_code == status.HTTP_201_CREATED:
            print("✅ Top-up created successfully")
            data = response.data
            print(f"   - Top-up ID: {data['topup']['id']}")
            print(f"   - Amount: ${data['topup']['amount_minor'] / 100:.2f}")
            print(f"   - Track ID: {data.get('payment', {}).get('track_id', 'N/A')}")
            return data.get('payment', {}).get('track_id')
        else:
            print(f"❌ Top-up creation failed: {response.status_code}")
            print(f"   Response: {response.data}")
            return None
    except Exception as e:
        print(f"❌ Error creating top-up: {e}")
        return None

def test_webhook_validation(track_id, user):
    """Test webhook validation"""
    print_section("3. Webhook Validation")
    
    if not track_id:
        print("⚠️  Skipping webhook test (no track_id)")
        return
    
    # Create a payment record first
    network = CryptoNetwork.objects.filter(is_active=True).first()
    payment = OxaPayPayment.objects.create(
        user=user,
        track_id=track_id,
        network=network,
        address='bc1qtest123',
        amount=10.0,
        pay_amount=0.00015,
        pay_currency='btc',
        currency='usd',
        status='pending'
    )
    print(f"✅ Created payment record: {track_id}")
    
    # Test webhook payload
    payload = {
        "track_id": track_id,
        "status": "Paid",
        "type": "white_label",
        "amount": 10.0,
        "value": 0.00015,
        "currency": "BTC",
        "txs": [{
            "status": "confirmed",
            "tx_hash": "test_hash_123",
            "sent_amount": 10.0,
            "received_amount": 9.95,
            "currency": "BTC",
            "network": "Bitcoin Network",
            "address": "bc1qtest123",
            "confirmations": 6
        }]
    }
    
    # Calculate HMAC
    api_key = getattr(settings, 'OXAPAY_API_KEY', 'test_key')
    body = json.dumps(payload)
    hmac_sig = hmac.new(
        api_key.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    # Create mock request
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.post(
        '/api/v2/wallet/webhook/',
        data=body,
        content_type='application/json',
        HTTP_HMAC=hmac_sig
    )
    
    try:
        response = oxapay_webhook(request)
        if response.status_code == 200:
            print("✅ Webhook processed successfully")
            print(f"   - Response: {response.content.decode()}")
            
            # Check if wallet was credited
            wallet = Wallet.objects.get(user=user)
            print(f"   - Wallet balance: ${wallet.balance_minor / 100:.2f}")
            
            # Check payment status
            payment.refresh_from_db()
            print(f"   - Payment status: {payment.status}")
            
            return True
        else:
            print(f"❌ Webhook failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_duplicate_prevention(user):
    """Test duplicate payment prevention"""
    print_section("4. Duplicate Payment Prevention")
    
    # Get a paid payment
    payment = OxaPayPayment.objects.filter(
        user=user,
        status='paid'
    ).first()
    
    if not payment:
        print("⚠️  No paid payment found, skipping duplicate test")
        return
    
    # Get initial wallet balance
    wallet = Wallet.objects.get(user=user)
    initial_balance = wallet.balance_minor
    
    # Try to process same payment again
    payload = {
        "track_id": payment.track_id,
        "status": "Paid",
        "amount": payment.amount
    }
    
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.post(
        '/api/v2/wallet/webhook/',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    try:
        response = oxapay_webhook(request)
        wallet.refresh_from_db()
        
        if wallet.balance_minor == initial_balance:
            print("✅ Duplicate payment prevented")
            print(f"   - Balance unchanged: ${wallet.balance_minor / 100:.2f}")
        else:
            print(f"❌ Duplicate payment was processed!")
            print(f"   - Balance changed from ${initial_balance / 100:.2f} to ${wallet.balance_minor / 100:.2f}")
    except Exception as e:
        print(f"❌ Error testing duplicate prevention: {e}")

def test_error_cases(user):
    """Test error cases"""
    print_section("5. Error Cases")
    
    factory = APIRequestFactory()
    
    # Test 1: Missing amount_minor
    print("Test 1: Missing amount_minor")
    request = factory.post('/api/v2/wallet/topups/', {
        'network_id': str(CryptoNetwork.objects.first().id)
    }, format='json')
    request.user = user
    
    viewset = TopUpIntentV2ViewSet()
    viewset.request = request
    
    try:
        response = viewset.create(request)
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print("   ✅ Correctly rejected missing amount_minor")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Zero amount
    print("Test 2: Zero amount")
    request = factory.post('/api/v2/wallet/topups/', {
        'amount_minor': 0,
        'network_id': str(CryptoNetwork.objects.first().id)
    }, format='json')
    request.user = user
    
    viewset = TopUpIntentV2ViewSet()
    viewset.request = request
    
    try:
        response = viewset.create(request)
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print("   ✅ Correctly rejected zero amount")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Invalid network_id
    print("Test 3: Invalid network_id")
    request = factory.post('/api/v2/wallet/topups/', {
        'amount_minor': 1000,
        'network_id': '00000000-0000-0000-0000-000000000000'
    }, format='json')
    request.user = user
    
    viewset = TopUpIntentV2ViewSet()
    viewset.request = request
    
    try:
        response = viewset.create(request)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            print("   ✅ Correctly rejected invalid network_id")
        else:
            print(f"   ❌ Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  TOP-UP VALIDATION SYSTEM TEST")
    print("="*60)
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='test@example.com',
        defaults={
            'email': 'test@example.com',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"\n✅ Created test user: {user.email}")
    else:
        print(f"\n✅ Using existing test user: {user.email}")
    
    # Run tests
    network = test_network_validation()
    if not network:
        print("❌ No active networks found. Please create networks first.")
        return
    
    track_id = test_topup_creation(user, network)
    test_webhook_validation(track_id, user)
    test_duplicate_prevention(user)
    test_error_cases(user)
    
    print_section("Test Summary")
    print("✅ All tests completed!")
    print("\nFor detailed testing, see: TOPUP_VALIDATION_TESTING_GUIDE.md")

if __name__ == '__main__':
    main()







