"""
Test OXA Pay with alternative authentication methods
Sometimes APIs expect headers in different formats
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

def test_alternative_auth_methods():
    """Test different ways of sending the API key"""
    api_key = os.getenv('OXAPAY_API_KEY')
    
    if not api_key:
        print("Please set OXAPAY_API_KEY environment variable or provide it:")
        api_key = input("API Key: ").strip()
        if not api_key:
            print("❌ No API key provided")
            return
    
    api_key = api_key.strip()
    url = "https://api.oxapay.com/v1/payment/static-address"
    payload = {'network': 'Bitcoin Network'}
    
    print("=" * 60)
    print("Testing Alternative Authentication Methods")
    print("=" * 60)
    print(f"\nAPI Key length: {len(api_key)}")
    print(f"API Key preview: {api_key[:10]}...{api_key[-4:]}")
    
    # Method 1: Standard header (current implementation)
    print("\n" + "-" * 60)
    print("Method 1: merchant_api_key header (standard)")
    print("-" * 60)
    try:
        headers = {
            'Content-Type': 'application/json',
            'merchant_api_key': api_key
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS with standard header!")
            data = response.json()
            print(f"Track ID: {data.get('data', {}).get('track_id', 'N/A')}")
            return True
        else:
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error = data.get('error', {})
            print(f"❌ Failed: {error.get('message', response.text[:100])}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Method 2: Authorization header
    print("\n" + "-" * 60)
    print("Method 2: Authorization header")
    print("-" * 60)
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS with Authorization header!")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Method 3: API key in body
    print("\n" + "-" * 60)
    print("Method 3: API key in request body")
    print("-" * 60)
    try:
        headers = {'Content-Type': 'application/json'}
        payload_with_key = {**payload, 'merchant_api_key': api_key}
        response = requests.post(url, json=payload_with_key, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS with API key in body!")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Method 4: Query parameter
    print("\n" + "-" * 60)
    print("Method 4: API key as query parameter")
    print("-" * 60)
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            f"{url}?merchant_api_key={api_key}",
            json=payload,
            headers=headers,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS with query parameter!")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("All methods failed. Possible issues:")
    print("=" * 60)
    print("1. API key is incorrect or expired")
    print("2. API key needs to be activated in OXA Pay dashboard")
    print("3. Account doesn't have API access enabled")
    print("4. Network name 'Bitcoin Network' is incorrect")
    print("5. API endpoint URL is wrong")
    print("\nCheck OXA Pay dashboard:")
    print("- Settings → API Keys")
    print("- Verify the key is active")
    print("- Check if there are any restrictions")
    
    return False

if __name__ == '__main__':
    test_alternative_auth_methods()

