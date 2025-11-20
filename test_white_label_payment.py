"""
Test white-label payment with exact format to debug 400 error
"""
import requests
import json
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import CryptoNetwork
from dotenv import load_dotenv
load_dotenv()

def test_white_label():
    """Test white-label payment with detailed logging"""
    api_key = os.getenv('OXAPAY_API_KEY')
    if not api_key:
        print("Please provide API key:")
        api_key = input().strip()
    
    if not api_key:
        print("❌ No API key")
        return False
    
    api_key = api_key.strip()
    
    # Get a network
    networks = CryptoNetwork.objects.filter(is_active=True)
    if networks.count() == 0:
        print("❌ No networks")
        return False
    
    test_network = networks.first()
    print(f"Testing with: {test_network.name} ({test_network.key})")
    
    # Map network
    network_map = {
        'btc': 'Bitcoin Network',
        'eth': 'Ethereum Network',
        'tron': 'TRON',
    }
    oxa_network = network_map.get(test_network.key.lower(), test_network.name)
    pay_currency = test_network.native_symbol.lower()
    
    print(f"OXA Pay network: {oxa_network}")
    print(f"Pay currency: {pay_currency}")
    
    url = 'https://api.oxapay.com/v1/payment/white-label'
    
    headers = {
        'merchant_api_key': api_key,
        'Content-Type': 'application/json'
    }
    
    # Test with different payload formats
    test_cases = [
        {
            'name': 'Minimal required fields',
            'data': {
                'amount': 10.0,
                'pay_currency': pay_currency,
            }
        },
        {
            'name': 'With network',
            'data': {
                'amount': 10.0,
                'pay_currency': pay_currency,
                'network': oxa_network,
            }
        },
        {
            'name': 'Full payload',
            'data': {
                'amount': 10.0,
                'pay_currency': pay_currency,
                'currency': 'usd',
                'network': oxa_network,
                'lifetime': 60,
                'auto_withdrawal': 1,
                'under_paid_coverage': 1.0,
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}: {test_case['name']}")
        print('=' * 70)
        print(f"Payload: {json.dumps(test_case['data'], indent=2)}")
        
        try:
            response = requests.post(url, data=json.dumps(test_case['data']), headers=headers, timeout=30)
            
            print(f"Status: {response.status_code}")
            
            try:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                
                if response.status_code == 200 and result.get('status') == 200:
                    print("✅ SUCCESS!")
                    return True
                else:
                    error = result.get('error', {})
                    print(f"❌ Error: {error.get('message')} (key: {error.get('key')}, type: {error.get('type')})")
                    
            except:
                print(f"Response (not JSON): {response.text[:500]}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    return False

if __name__ == '__main__':
    test_white_label()

