"""
Debug script to test OXA Pay API request format
Shows exactly what's being sent and received
"""
import os
import sys
import django
import requests
import json

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from dotenv import load_dotenv
load_dotenv()

def test_raw_request():
    """Test OXA Pay API with raw requests to see exact format"""
    api_key = os.getenv('OXAPAY_API_KEY')
    
    if not api_key:
        print("❌ OXAPAY_API_KEY not found in environment")
        return
    
    print("=" * 60)
    print("OXA Pay API Debug Test")
    print("=" * 60)
    print(f"\nAPI Key (first 10 chars): {api_key[:10]}...")
    print(f"API Key length: {len(api_key)}")
    
    url = "https://api.oxapay.com/v1/payment/static-address"
    
    headers = {
        'Content-Type': 'application/json',
        'merchant_api_key': api_key
    }
    
    payload = {
        'network': 'Bitcoin Network'
    }
    
    print("\n" + "-" * 60)
    print("Request Details:")
    print("-" * 60)
    print(f"URL: {url}")
    print(f"Method: POST")
    print(f"Headers:")
    for key, value in headers.items():
        if 'api_key' in key.lower():
            print(f"  {key}: {value[:10]}...{value[-4:] if len(value) > 14 else ''} (length: {len(value)})")
        else:
            print(f"  {key}: {value}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    print("\n" + "-" * 60)
    print("Sending request...")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
            
            if response.status_code == 401:
                error = data.get('error', {})
                print("\n" + "=" * 60)
                print("401 Unauthorized Error Details:")
                print("=" * 60)
                print(f"Error Type: {error.get('type', 'N/A')}")
                print(f"Error Key: {error.get('key', 'N/A')}")
                print(f"Error Message: {error.get('message', 'N/A')}")
                print("\nPossible issues:")
                print("1. API key is incorrect or expired")
                print("2. API key format is wrong (should be merchant API key, not other key type)")
                print("3. Account may not have API access enabled")
                print("4. API key may need to be activated in OXA Pay dashboard")
                
        except:
            print(response.text)
        
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_raw_request()

