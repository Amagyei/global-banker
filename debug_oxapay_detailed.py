"""
Detailed debug script to see exactly what's being sent to OXA Pay
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

def test_with_detailed_logging():
    """Test with maximum detail"""
    api_key = os.getenv('OXAPAY_API_KEY')
    
    if not api_key:
        print("Please provide API key:")
        api_key = input().strip()
    
    if not api_key:
        print("❌ No API key")
        return
    
    api_key = api_key.strip()
    url = "https://api.oxapay.com/v1/payment/static-address"
    
    # Test different header formats
    test_cases = [
        {
            'name': 'Standard header (merchant_api_key)',
            'headers': {
                'Content-Type': 'application/json',
                'merchant_api_key': api_key
            }
        },
        {
            'name': 'Header with X- prefix',
            'headers': {
                'Content-Type': 'application/json',
                'X-Merchant-Api-Key': api_key
            }
        },
        {
            'name': 'Authorization Bearer',
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
        },
        {
            'name': 'Authorization with merchant_api_key',
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': f'merchant_api_key {api_key}'
            }
        }
    ]
    
    payload = {'network': 'Bitcoin Network'}
    
    print("=" * 70)
    print("OXA Pay Detailed Debug Test")
    print("=" * 70)
    print(f"\nAPI Key: {api_key[:15]}...{api_key[-5:]}")
    print(f"API Key length: {len(api_key)}")
    print(f"API Key type: {type(api_key)}")
    print(f"API Key has whitespace: {api_key != api_key.strip()}")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}: {test_case['name']}")
        print('=' * 70)
        
        headers = test_case['headers']
        print(f"\nRequest Headers:")
        for key, value in headers.items():
            if 'key' in key.lower() or 'auth' in key.lower():
                print(f"  {key}: {value[:15]}...{value[-5:]} (length: {len(value)})")
            else:
                print(f"  {key}: {value}")
        
        print(f"\nRequest Payload:")
        print(json.dumps(payload, indent=2))
        
        try:
            # Create a session to see what requests actually sends
            session = requests.Session()
            session.headers.update(headers)
            
            # Prepare request
            req = requests.Request('POST', url, json=payload)
            prepped = session.prepare_request(req)
            
            print(f"\nPrepared Request Headers (what will be sent):")
            for key, value in prepped.headers.items():
                if 'key' in key.lower() or 'auth' in key.lower():
                    print(f"  {key}: {value[:15]}...{value[-5:]} (length: {len(value)})")
                else:
                    print(f"  {key}: {value}")
            
            # Send request
            response = session.send(prepped, timeout=30)
            
            print(f"\nResponse:")
            print(f"  Status Code: {response.status_code}")
            print(f"  Status Text: {response.reason}")
            
            print(f"\nResponse Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            print(f"\nResponse Body:")
            try:
                data = response.json()
                print(json.dumps(data, indent=2))
                
                if response.status_code == 200:
                    print(f"\n✅ SUCCESS!")
                    print(f"Track ID: {data.get('data', {}).get('track_id', 'N/A')}")
                    print(f"Address: {data.get('data', {}).get('address', 'N/A')}")
                    return True
                elif response.status_code == 401:
                    error = data.get('error', {})
                    print(f"\n❌ 401 Unauthorized")
                    print(f"Error Type: {error.get('type', 'N/A')}")
                    print(f"Error Key: {error.get('key', 'N/A')}")
                    print(f"Error Message: {error.get('message', 'N/A')}")
                    
            except:
                print(response.text[:500])
                
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 70}")
    print("All tests completed")
    print("=" * 70)
    return False

if __name__ == '__main__':
    test_with_detailed_logging()

