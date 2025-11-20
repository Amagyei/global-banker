#!/usr/bin/env python
"""
Send Bitcoin from a WIF private key to a specified address.
Handles both testnet and mainnet.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.exchange_rates import get_exchange_rate
from decimal import Decimal
import time

# Configuration
WIF_KEY = "cVn9pUq3bLWadJZ4JZVLoGPWnxZ1Pg5ayZ35yX5KGPRrFwrygHqW"
TO_ADDRESS = "bc1qqkc4eel5ujd6vexturqrtnn2pnhtep0yqsz0p0"
USD_AMOUNT = 10.0

print("=" * 80)
print("BITCOIN TRANSACTION SENDER")
print("=" * 80)
print()

# Detect network from WIF key
# Testnet WIF keys start with 'c' or '9' for uncompressed, 'c' for compressed
# Mainnet WIF keys start with '5' or 'K'/'L' for uncompressed, 'K'/'L' for compressed
is_testnet = WIF_KEY[0] in ['c', '9']  # Testnet WIF typically starts with 'c'

# Detect destination network from address
is_dest_testnet = TO_ADDRESS.startswith('tb1') or TO_ADDRESS.startswith('2') or TO_ADDRESS.startswith('m') or TO_ADDRESS.startswith('n')
is_dest_mainnet = TO_ADDRESS.startswith('bc1') or TO_ADDRESS.startswith('1') or TO_ADDRESS.startswith('3')

print(f"Source Network: {'Testnet' if is_testnet else 'Mainnet'}")
print(f"Destination Address: {TO_ADDRESS}")
print(f"Destination Network: {'Testnet' if is_dest_testnet else 'Mainnet' if is_dest_mainnet else 'Unknown'}")
print()

# Check network mismatch
if is_testnet and is_dest_mainnet:
    print("⚠️  WARNING: Cannot send from testnet to mainnet!")
    print("   Testnet coins cannot be sent to mainnet addresses.")
    print("   Please use a testnet address (starts with tb1, m, n, or 2)")
    sys.exit(1)
elif not is_testnet and is_dest_testnet:
    print("⚠️  WARNING: Cannot send from mainnet to testnet!")
    print("   Mainnet coins cannot be sent to testnet addresses.")
    sys.exit(1)

# Get exchange rate
print("Fetching Bitcoin exchange rate...")
try:
    btc_rate = get_exchange_rate('BTC', 'USD')
    print(f"Current BTC/USD rate: ${float(btc_rate):,.2f}")
except Exception as e:
    print(f"Error fetching exchange rate: {e}")
    # Use fallback rate
    btc_rate = Decimal('50000.00')
    print(f"Using fallback rate: ${float(btc_rate):,.2f}")

# Calculate BTC amount
btc_amount = Decimal(USD_AMOUNT) / btc_rate
btc_amount_satoshi = int(btc_amount * Decimal(10**8))

print(f"\nAmount to send: ${USD_AMOUNT:.2f} USD")
print(f"Equivalent BTC: {btc_amount:.8f} BTC")
print(f"Equivalent Satoshi: {btc_amount_satoshi:,} satoshi")
print()

# Try using bit library (simpler)
try:
    if is_testnet:
        from bit import PrivateKeyTestnet as PrivateKey
        network_name = "testnet"
        explorer_url = "https://blockstream.info/testnet"
        broadcast_url = "https://blockstream.info/testnet/api/tx"
    else:
        from bit import PrivateKey
        network_name = "mainnet"
        explorer_url = "https://blockstream.info"
        broadcast_url = "https://blockstream.info/api/tx"
    
    print(f"Initializing private key for {network_name}...")
    key = PrivateKey(WIF_KEY)
    
    # Get balance
    print(f"Checking balance for {key.address}...")
    balance_btc_str = key.get_balance()
    balance_btc = float(balance_btc_str)
    balance_satoshi = int(balance_btc * 1e8)
    
    print(f"Current balance: {balance_btc:.8f} BTC ({balance_satoshi:,} satoshi)")
    
    # Estimate fee (rough estimate: 1000 satoshi for testnet, 10000 for mainnet)
    estimated_fee_satoshi = 1000 if is_testnet else 10000
    estimated_fee_btc = estimated_fee_satoshi / 1e8
    
    total_needed_satoshi = btc_amount_satoshi + estimated_fee_satoshi
    total_needed_btc = total_needed_satoshi / 1e8
    
    print(f"\nEstimated fee: {estimated_fee_satoshi:,} satoshi ({estimated_fee_btc:.8f} BTC)")
    print(f"Total needed: {total_needed_satoshi:,} satoshi ({total_needed_btc:.8f} BTC)")
    
    if balance_satoshi < total_needed_satoshi:
        shortfall_satoshi = total_needed_satoshi - balance_satoshi
        shortfall_btc = shortfall_satoshi / 1e8
        print(f"\n❌ Insufficient balance!")
        print(f"   Shortfall: {shortfall_satoshi:,} satoshi ({shortfall_btc:.8f} BTC)")
        sys.exit(1)
    
    print(f"\n✅ Sufficient balance. Proceeding with transaction...")
    print()
    
    # Create and send transaction
    print(f"Sending {btc_amount:.8f} BTC to {TO_ADDRESS}...")
    
    # Use bit library's send method (handles fee estimation automatically)
    try:
        tx_hash = key.send([(TO_ADDRESS, btc_amount, 'btc')])
        print(f"\n✅ Transaction broadcast successfully!")
        print(f"Transaction Hash: {tx_hash}")
        print(f"\nView on explorer:")
        print(f"  {explorer_url}/tx/{tx_hash}")
        print(f"\nWaiting 2 seconds for propagation...")
        time.sleep(2)
        
        # Verify transaction
        import requests
        verify_url = f"{broadcast_url.replace('/api/tx', '')}/tx/{tx_hash}"
        try:
            response = requests.get(verify_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Transaction verified on blockchain explorer")
            else:
                print(f"⚠️  Transaction may still be propagating (status: {response.status_code})")
        except:
            print(f"⚠️  Could not verify transaction (may still be propagating)")
        
    except Exception as e:
        print(f"\n❌ Error sending transaction: {e}")
        print("\nTrying manual broadcast...")
        
        # Fallback: manual broadcast
        try:
            # Create transaction
            tx_hex = key.create_transaction([(TO_ADDRESS, btc_amount, 'btc')])
            
            # Broadcast manually
            import requests
            response = requests.post(
                broadcast_url,
                data=tx_hex,
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )
            
            if response.status_code == 200:
                tx_hash = response.text.strip()
                print(f"\n✅ Transaction broadcast successfully!")
                print(f"Transaction Hash: {tx_hash}")
                print(f"\nView on explorer:")
                print(f"  {explorer_url}/tx/{tx_hash}")
            else:
                print(f"\n❌ Broadcast failed: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e2:
            print(f"\n❌ Manual broadcast also failed: {e2}")
            sys.exit(1)
    
except ImportError:
    print("❌ 'bit' library not installed")
    print("Install with: pip install bit")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("Transaction completed!")
print("=" * 80)

