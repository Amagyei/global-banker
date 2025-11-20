"""
Interactive OXA Pay test script
Prompts for API key and tests the integration
"""
import os
import sys
import django
import getpass

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.oxa_pay_client import OxaPayClient
from wallet.models import CryptoNetwork

def main():
    print("=" * 60)
    print("OXA Pay Integration Test")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv('OXAPAY_API_KEY')
    
    if not api_key:
        print("\nOXA Pay API key not found in environment.")
        print("Please provide your OXA Pay merchant API key.")
        api_key = getpass.getpass("API Key: ").strip()
        
        if not api_key:
            print("❌ No API key provided. Exiting.")
            return False
        
        # Set in environment for this session
        os.environ['OXAPAY_API_KEY'] = api_key
    
    print(f"\n✅ Using API key: {api_key[:10]}...{api_key[-4:]}")
    
    # Initialize client
    try:
        client = OxaPayClient()
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Get networks
    networks = CryptoNetwork.objects.filter(is_active=True)
    if networks.count() == 0:
        print("❌ No active networks found in database")
        return False
    
    print(f"\n✅ Found {networks.count()} active network(s)")
    for i, net in enumerate(networks, 1):
        print(f"   {i}. {net.name} ({net.key}) - {net.native_symbol}")
    
    test_network = networks.first()
    print(f"\n📝 Testing with: {test_network.name}")
    
    # Map network
    network_map = {
        'btc': 'Bitcoin Network',
        'eth': 'Ethereum Network',
    }
    oxa_network = network_map.get(test_network.key.lower(), test_network.name)
    print(f"   OXA Pay network: {oxa_network}")
    
    # Test 1: Static Address
    print("\n" + "-" * 60)
    print("Test 1: Generate Static Address")
    print("-" * 60)
    try:
        result = client.generate_static_address(
            network=oxa_network,
            description='Test static address from integration test',
            auto_withdrawal=True
        )
        print("✅ SUCCESS!")
        print(f"   Track ID: {result.get('track_id')}")
        print(f"   Address: {result.get('address')}")
        if result.get('qr_code'):
            print(f"   QR Code: {result.get('qr_code')[:60]}...")
        print(f"   Date: {result.get('date')}")
    except ValueError as e:
        print(f"❌ API Error: {e}")
        print("   This could mean:")
        print("   - Invalid API key")
        print("   - Network name not recognized by OXA Pay")
        print("   - OXA Pay service issue")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: White-Label Payment
    print("\n" + "-" * 60)
    print("Test 2: Generate White-Label Payment ($10 USD)")
    print("-" * 60)
    try:
        result = client.generate_white_label_payment(
            amount=10.0,
            pay_currency=test_network.native_symbol.lower(),
            currency='usd',
            network=oxa_network,
            lifetime=60,
            description='Test payment from integration test',
            auto_withdrawal=True,
            under_paid_coverage=1.0
        )
        print("✅ SUCCESS!")
        print(f"   Track ID: {result.get('track_id')}")
        print(f"   Address: {result.get('address')}")
        print(f"   Amount: {result.get('amount')} {result.get('currency', 'usd').upper()}")
        print(f"   Pay Amount: {result.get('pay_amount')} {result.get('pay_currency', '').upper()}")
        if result.get('rate'):
            print(f"   Exchange Rate: {result.get('rate')}")
        if result.get('qr_code'):
            print(f"   QR Code: {result.get('qr_code')[:60]}...")
        if result.get('expired_at'):
            from datetime import datetime
            expired = datetime.fromtimestamp(result.get('expired_at'))
            print(f"   Expires: {expired}")
    except ValueError as e:
        print(f"❌ API Error: {e}")
        print("   This could mean:")
        print("   - Invalid API key")
        print("   - Network/currency not supported")
        print("   - OXA Pay service issue")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYour OXA Pay integration is working correctly.")
    print("You can now use the API v2 endpoints:")
    print("  - POST /api/v2/wallet/topups/")
    print("  - GET /api/v2/wallet/oxapay/payments/")
    print("  - POST /api/v2/wallet/oxapay/static-addresses/")
    print("\nDon't forget to:")
    print("  1. Add OXAPAY_API_KEY to your .env file")
    print("  2. Configure cold wallet addresses in OXA Pay dashboard")
    print("  3. Set up webhook URL: /api/v2/wallet/oxapay/webhook/")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

