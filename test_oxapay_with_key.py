"""
Test OXA Pay with API key provided as argument or environment variable
Usage: python test_oxapay_with_key.py [api_key]
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

def test_with_key(api_key=None):
    """Test OXA Pay with provided API key"""
    if api_key:
        os.environ['OXAPAY_API_KEY'] = api_key
        print(f"✅ Using provided API key: {api_key[:10]}...{api_key[-4:]}")
    elif os.getenv('OXAPAY_API_KEY'):
        api_key = os.getenv('OXAPAY_API_KEY')
        print(f"✅ Using API key from environment: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("❌ No API key provided")
        print("Usage: python test_oxapay_with_key.py [api_key]")
        print("   Or set OXAPAY_API_KEY environment variable")
        return False
    
    print("\n" + "=" * 60)
    print("Testing OXA Pay Client")
    print("=" * 60)
    
    try:
        client = OxaPayClient()
        print("✅ Client initialized")
        
        # Get networks
        networks = CryptoNetwork.objects.filter(is_active=True)
        if networks.count() == 0:
            print("❌ No active networks found")
            return False
        
        test_network = networks.first()
        print(f"\n✅ Testing with network: {test_network.name} ({test_network.key})")
        
        # Map network
        network_map = {
            'btc': 'Bitcoin Network',
            'eth': 'Ethereum Network',
        }
        oxa_network = network_map.get(test_network.key.lower(), test_network.name)
        
        # Test 1: Static address
        print(f"\n1. Testing static address generation...")
        try:
            result = client.generate_static_address(
                network=oxa_network,
                description='Test static address',
                auto_withdrawal=True
            )
            print("✅ Static address generated!")
            print(f"   Track ID: {result.get('track_id')}")
            print(f"   Address: {result.get('address')}")
            print(f"   QR Code: {result.get('qr_code', 'N/A')[:60]}...")
        except Exception as e:
            print(f"❌ Static address failed: {e}")
            return False
        
        # Test 2: White-label payment
        print(f"\n2. Testing white-label payment ($10 USD)...")
        try:
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
            print("✅ White-label payment generated!")
            print(f"   Track ID: {result.get('track_id')}")
            print(f"   Address: {result.get('address')}")
            print(f"   Amount: {result.get('amount')} {result.get('currency', 'usd').upper()}")
            print(f"   Pay Amount: {result.get('pay_amount')} {result.get('pay_currency', '').upper()}")
            print(f"   Rate: {result.get('rate')}")
            print(f"   Expires: {result.get('expired_at')}")
        except Exception as e:
            print(f"❌ White-label payment failed: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    success = test_with_key(api_key)
    sys.exit(0 if success else 1)

