"""
Test OXA Pay using the exact format from their documentation example
"""
import requests
import json
import os
import sys
import django

# Setup Django for network lookup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import CryptoNetwork
from dotenv import load_dotenv
load_dotenv()

def test_exact_format():
    """Test using exact format from OXA Pay documentation"""
    
    # Get API key
    api_key = os.getenv('OXAPAY_API_KEY')
    if not api_key:
        print("Please provide your OXA Pay API key:")
        api_key = input().strip()
    
    if not api_key:
        print("❌ No API key provided")
        return False
    
    api_key = api_key.strip()
    
    print("=" * 70)
    print("OXA Pay Test - Exact Documentation Format")
    print("=" * 70)
    print(f"\nAPI Key: {api_key[:15]}...{api_key[-5:]}")
    
    # Get network
    networks = CryptoNetwork.objects.filter(is_active=True)
    if networks.count() == 0:
        print("❌ No active networks")
        return False
    
    test_network = networks.first()
    print(f"Network: {test_network.name} ({test_network.key})")
    
    # Map to OXA Pay network name
    network_map = {
        'btc': 'Bitcoin Network',
        'eth': 'Ethereum Network',
        'tron': 'TRON',
    }
    oxa_network = network_map.get(test_network.key.lower(), test_network.name)
    print(f"OXA Pay Network: {oxa_network}")
    
    # Test 1: Static Address (exact format from docs)
    print("\n" + "-" * 70)
    print("Test 1: Static Address (Exact Documentation Format)")
    print("-" * 70)
    
    url = 'https://api.oxapay.com/v1/payment/static-address'
    
    headers = {
        'merchant_api_key': api_key,
        'Content-Type': 'application/json'
    }
    
    data = {
        "network": oxa_network,
        "auto_withdrawal": False,  # Changed from True to match example
        "description": "Test static address"
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Headers:")
    for k, v in headers.items():
        if 'key' in k.lower():
            print(f"  {k}: {v[:15]}...{v[-5:]}")
        else:
            print(f"  {k}: {v}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        # Exact format from documentation
        response = requests.post(url, data=json.dumps(data), headers=headers)
        result = response.json()
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(result, indent=2))
        
        if response.status_code == 200 and result.get('status') == 200:
            print("\n✅ SUCCESS!")
            data_result = result.get('data', {})
            print(f"Track ID: {data_result.get('track_id', 'N/A')}")
            print(f"Address: {data_result.get('address', 'N/A')}")
            return True
        else:
            error = result.get('error', {})
            print(f"\n❌ Failed")
            print(f"Error Type: {error.get('type', 'N/A')}")
            print(f"Error Key: {error.get('key', 'N/A')}")
            print(f"Error Message: {error.get('message', 'N/A')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_exact_format()
    sys.exit(0 if success else 1)

