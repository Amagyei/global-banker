"""
Test OXA Pay with the specific body format provided
"""
import requests
import json
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from dotenv import load_dotenv
load_dotenv()

def test_with_specific_body():
    """Test with the exact body format provided"""
    
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
    print("OXA Pay Test - Specific Body Format")
    print("=" * 70)
    print(f"\nAPI Key: {api_key[:15]}...{api_key[-5:]}")
    
    url = 'https://api.oxapay.com/v1/payment/static-address'
    
    headers = {
        'merchant_api_key': api_key,
        'Content-Type': 'application/json'
    }
    
    # Exact body as provided
    data = {
        "network": "TRON",
        "to_currency": "USDT",
        "auto_withdrawal": 0,
        "callback_url": "http://bvnkpro.com/finance",
        "email": "kilt@mail.com",
        "order_id": "2323",
        "description": "asdasd"
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Headers:")
    for k, v in headers.items():
        if 'key' in k.lower():
            print(f"  {k}: {v[:15]}...{v[-5:]}")
        else:
            print(f"  {k}: {v}")
    print(f"\nRequest Body:")
    print(json.dumps(data, indent=2))
    
    try:
        # Exact format from documentation
        response = requests.post(url, data=json.dumps(data), headers=headers)
        
        print(f"\n" + "-" * 70)
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
        
        try:
            result = response.json()
            print(f"\nResponse Body:")
            print(json.dumps(result, indent=2))
            
            if response.status_code == 200 and result.get('status') == 200:
                print("\n" + "=" * 70)
                print("✅ SUCCESS!")
                print("=" * 70)
                data_result = result.get('data', {})
                print(f"Track ID: {data_result.get('track_id', 'N/A')}")
                print(f"Address: {data_result.get('address', 'N/A')}")
                print(f"Network: {data_result.get('network', 'N/A')}")
                if data_result.get('qr_code'):
                    print(f"QR Code: {data_result.get('qr_code', 'N/A')[:60]}...")
                return True
            else:
                print("\n" + "=" * 70)
                print("❌ FAILED")
                print("=" * 70)
                error = result.get('error', {})
                print(f"Error Type: {error.get('type', 'N/A')}")
                print(f"Error Key: {error.get('key', 'N/A')}")
                print(f"Error Message: {error.get('message', 'N/A')}")
                print(f"Status: {result.get('status', 'N/A')}")
                return False
                
        except json.JSONDecodeError:
            print(f"\nResponse Body (not JSON):")
            print(response.text[:500])
            return False
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_with_specific_body()
    sys.exit(0 if success else 1)

