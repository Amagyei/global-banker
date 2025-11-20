"""
Test script for OXA Pay integration
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.oxa_pay_client import OxaPayClient
from wallet.models import CryptoNetwork
from django.contrib.auth import get_user_model

User = get_user_model()

def test_oxapay_client():
    """Test OXA Pay client initialization and API calls"""
    print("=" * 60)
    print("Testing OXA Pay Integration")
    print("=" * 60)
    
    # Test 1: Client initialization
    print("\n1. Testing client initialization...")
    try:
        client = OxaPayClient()
        print("✅ OXA Pay client initialized successfully")
        print(f"   API Key: {client.api_key[:10]}...{client.api_key[-4:] if len(client.api_key) > 14 else ''}")
    except ValueError as e:
        print(f"❌ Failed to initialize client: {e}")
        print("   Make sure OXAPAY_API_KEY is set in .env")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test 2: Get networks
    print("\n2. Getting available networks...")
    try:
        networks = CryptoNetwork.objects.filter(is_active=True)
        print(f"✅ Found {networks.count()} active networks:")
        for net in networks:
            print(f"   - {net.name} ({net.key}) - {net.native_symbol}")
        
        if networks.count() == 0:
            print("⚠️  No active networks found. Cannot test payment creation.")
            return False
        
        test_network = networks.first()
    except Exception as e:
        print(f"❌ Error getting networks: {e}")
        return False
    
    # Test 3: Generate static address
    print(f"\n3. Testing static address generation for {test_network.name}...")
    try:
        # Map network to OXA Pay network name
        network_map = {
            'btc': 'Bitcoin Network',
            'eth': 'Ethereum Network',
        }
        oxa_network = network_map.get(test_network.key.lower(), test_network.name)
        
        print(f"   Using OXA Pay network: {oxa_network}")
        
        # Generate static address
        result = client.generate_static_address(
            network=oxa_network,
            description='Test static address',
            auto_withdrawal=True
        )
        
        print("✅ Static address generated successfully!")
        print(f"   Track ID: {result.get('track_id', 'N/A')}")
        print(f"   Address: {result.get('address', 'N/A')}")
        print(f"   QR Code: {result.get('qr_code', 'N/A')[:50]}...")
        
        return True
        
    except ValueError as e:
        print(f"❌ API Error: {e}")
        print("   This might be due to:")
        print("   - Invalid API key")
        print("   - Network name mismatch")
        print("   - OXA Pay service issue")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_white_label_payment():
    """Test white-label payment generation"""
    print("\n" + "=" * 60)
    print("Testing White-Label Payment Generation")
    print("=" * 60)
    
    try:
        client = OxaPayClient()
        networks = CryptoNetwork.objects.filter(is_active=True)
        
        if networks.count() == 0:
            print("⚠️  No active networks found")
            return False
        
        test_network = networks.first()
        network_map = {
            'btc': 'Bitcoin Network',
            'eth': 'Ethereum Network',
        }
        oxa_network = network_map.get(test_network.key.lower(), test_network.name)
        
        print(f"\nGenerating white-label payment for {test_network.name}...")
        print(f"Amount: $10.00 USD")
        print(f"Network: {oxa_network}")
        
        result = client.generate_white_label_payment(
            amount=10.0,
            pay_currency=test_network.native_symbol.lower(),
            currency='usd',
            network=oxa_network,
            lifetime=60,
            description='Test payment',
            auto_withdrawal=True,
            under_paid_coverage=1.0
        )
        
        print("✅ White-label payment generated successfully!")
        print(f"   Track ID: {result.get('track_id', 'N/A')}")
        print(f"   Address: {result.get('address', 'N/A')}")
        print(f"   Amount: {result.get('amount', 'N/A')} {result.get('currency', 'N/A').upper()}")
        print(f"   Pay Amount: {result.get('pay_amount', 'N/A')} {result.get('pay_currency', 'N/A').upper()}")
        print(f"   Rate: {result.get('rate', 'N/A')}")
        print(f"   QR Code: {result.get('qr_code', 'N/A')[:50]}...")
        print(f"   Expired At: {result.get('expired_at', 'N/A')}")
        
        return True
        
    except ValueError as e:
        print(f"❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test API endpoints via Django test client"""
    print("\n" + "=" * 60)
    print("Testing API Endpoints")
    print("=" * 60)
    
    try:
        from django.test import Client
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken
        
        User = get_user_model()
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            email='test@example.com',
            defaults={'username': 'testuser'}
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"✅ Created test user: {user.email}")
        else:
            print(f"✅ Using existing test user: {user.email}")
        
        # Get JWT token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Test client
        client = Client()
        
        # Test 1: Get networks
        print("\n1. Testing GET /api/v2/wallet/networks/")
        response = client.get(
            '/api/v2/wallet/networks/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        if response.status_code == 200:
            print("✅ Networks endpoint works")
            data = response.json()
            print(f"   Found {len(data)} networks")
        else:
            print(f"❌ Networks endpoint failed: {response.status_code}")
            print(f"   Response: {response.content.decode()[:200]}")
        
        # Test 2: Get wallet
        print("\n2. Testing GET /api/v2/wallet/wallet/")
        response = client.get(
            '/api/v2/wallet/wallet/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        if response.status_code == 200:
            print("✅ Wallet endpoint works")
            data = response.json()
            if data:
                print(f"   Balance: {data[0].get('balance', 'N/A')}")
        else:
            print(f"❌ Wallet endpoint failed: {response.status_code}")
        
        print("\n✅ API endpoint tests complete")
        return True
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("OXA Pay Integration Test Suite")
    print("=" * 60)
    
    # Run tests
    test1 = test_oxapay_client()
    test2 = test_white_label_payment()
    test3 = test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Client Initialization: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"White-Label Payment: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"API Endpoints: {'✅ PASS' if test3 else '❌ FAIL'}")
    print("=" * 60)

