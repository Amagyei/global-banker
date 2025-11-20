#!/usr/bin/env python
"""
Check if address exists in system, then send deposit if it's testnet compatible.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import DepositAddress
import requests
from decimal import Decimal

WIF_KEY = "cVn9pUq3bLWadJZ4JZVLoGPWnxZ1Pg5ayZ35yX5KGPRrFwrygHqW"
TO_ADDRESS = "bc1qqkc4eel5ujd6vexturqrtnn2pnhtep0yqsz0p0"
USD_AMOUNT = 10.0

print("=" * 80)
print("CHECKING ADDRESS AND SENDING DEPOSIT")
print("=" * 80)
print()

# Check if address exists in system
print(f"Checking if address exists in system: {TO_ADDRESS}")
deposit_addr = DepositAddress.objects.filter(address=TO_ADDRESS).first()

if deposit_addr:
    print(f"✅ Address found in system!")
    print(f"   User: {deposit_addr.user.email}")
    print(f"   Network: {deposit_addr.network.name}")
    print(f"   Is Testnet: {deposit_addr.network.effective_is_testnet}")
    print(f"   Active: {deposit_addr.is_active}")
    print()
    
    # Check network compatibility
    if deposit_addr.network.effective_is_testnet:
        print("✅ Address is testnet - compatible with source wallet")
        actual_address = deposit_addr.address
        print(f"   Using system address: {actual_address}")
        
        # Check if address format matches
        if actual_address.startswith('bc1'):
            print("⚠️  WARNING: Address in system has 'bc1' prefix but network is testnet!")
            print("   This might be a configuration issue.")
            print("   Proceeding with caution...")
        
        # Now send the deposit
        print(f"\n📊 Fetching exchange rate...")
        try:
            from wallet.exchange_rates import get_exchange_rate
            btc_rate = get_exchange_rate('BTC', 'USD')
            print(f"   Current BTC/USD rate: ${float(btc_rate):,.2f}")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            btc_rate = Decimal('50000.00')
            print(f"   Using fallback: ${float(btc_rate):,.2f}")
        
        btc_amount = Decimal(str(USD_AMOUNT)) / btc_rate
        print(f"\n💰 Sending ${USD_AMOUNT:.2f} USD = {float(btc_amount):.8f} BTC")
        print(f"   To: {actual_address}")
        
        # Import and use send_bitcoin function
        try:
            from send_bitcoin import send_bitcoin
            send_bitcoin(WIF_KEY, actual_address, float(USD_AMOUNT), 'testnet')
        except Exception as e:
            print(f"❌ Error sending: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Address is MAINNET but source wallet is TESTNET")
        print("   Cannot send from testnet to mainnet!")
        sys.exit(1)
else:
    print("❌ Address NOT found in system")
    print()
    print("The address you provided is:")
    print(f"  {TO_ADDRESS}")
    print()
    if TO_ADDRESS.startswith('bc1'):
        print("⚠️  This address starts with 'bc1' which indicates MAINNET")
        print("   Your source wallet is TESTNET (address starts with 'n')")
        print()
        print("Options:")
        print("1. If this should be a testnet address, it should start with 'tb1'")
        print("2. If you want to send to a different address, provide a testnet address")
        print("3. If this address is correct, you need a mainnet wallet to send to it")
    else:
        print("Please verify the address is correct and exists in the system.")
    sys.exit(1)

