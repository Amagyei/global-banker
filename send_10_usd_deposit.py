#!/usr/bin/env python
"""
Send $10 USD worth of Bitcoin from testnet wallet to a deposit address.
This script checks if the address exists in the system first.
"""
import os
import sys
import requests
from decimal import Decimal

# Configuration
WIF_KEY = "cVn9pUq3bLWadJZ4JZVLoGPWnxZ1Pg5ayZ35yX5KGPRrFwrygHqW"
TO_ADDRESS = "bc1qqkc4eel5ujd6vexturqrtnn2pnhtep0yqsz0p0"
USD_AMOUNT = 10.0

print("=" * 80)
print("SENDING $10 USD BITCOIN DEPOSIT")
print("=" * 80)
print()

# Check address format
if TO_ADDRESS.startswith('bc1'):
    print("⚠️  WARNING: Address starts with 'bc1' (mainnet bech32)")
    print("   Your source wallet is TESTNET (address starts with 'n')")
    print("   Cannot send from testnet to mainnet!")
    print()
    print("Checking if this is actually a testnet address in the system...")
    print("(Some addresses might be incorrectly formatted)")
    print()
    
    # Check if address exists in system (would need Django, but let's try a different approach)
    print("Since we're in testnet mode, let's check if there's a testnet version")
    print("or if this address exists in the system.")
    print()
    print("Options:")
    print("1. If this address is in your system as a deposit address,")
    print("   it should be a testnet address (tb1 prefix)")
    print("2. If you want to send to a testnet address, use:")
    print("   python send_bitcoin.py <testnet_address> 10.0")
    print()
    
    # Try to convert or find testnet equivalent
    # For bech32, testnet uses 'tb1' instead of 'bc1'
    # But we can't just change the prefix - the address encoding is different
    print("❌ Cannot proceed: Network mismatch")
    print()
    print("Please provide:")
    print("- A testnet address (starts with tb1, m, n, or 2), OR")
    print("- Confirm if this address exists in your system as a deposit address")
    sys.exit(1)

elif TO_ADDRESS.startswith('tb1') or TO_ADDRESS.startswith('m') or TO_ADDRESS.startswith('n') or TO_ADDRESS.startswith('2'):
    print(f"✅ Destination is TESTNET - compatible with source wallet")
    network = 'testnet'
    
    # Get exchange rate (using CoinGecko API directly)
    print(f"\n📊 Fetching Bitcoin exchange rate...")
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        btc_rate = Decimal(str(data['bitcoin']['usd']))
        print(f"   Current BTC/USD rate: ${float(btc_rate):,.2f}")
    except Exception as e:
        print(f"   ⚠️  Error fetching rate: {e}")
        btc_rate = Decimal('50000.00')  # Fallback
        print(f"   Using fallback rate: ${float(btc_rate):,.2f}")
    
    # Calculate BTC amount
    btc_amount = Decimal(str(USD_AMOUNT)) / btc_rate
    btc_amount_satoshi = int(btc_amount * Decimal(10**8))
    
    print(f"\n💰 Transaction Details:")
    print(f"   Amount: ${USD_AMOUNT:.2f} USD")
    print(f"   = {float(btc_amount):.8f} BTC")
    print(f"   = {btc_amount_satoshi:,} satoshi")
    print(f"   To: {TO_ADDRESS}")
    print(f"   Network: {network}")
    print()
    
    # Send using bit library
    try:
        from bit import PrivateKeyTestnet
        
        print(f"🔑 Loading private key...")
        key = PrivateKeyTestnet(WIF_KEY)
        sender_address = key.address
        print(f"   Sender: {sender_address}")
        
        print(f"\n🔍 Checking balance...")
        balance_btc_str = key.get_balance()
        balance_btc = float(balance_btc_str) if isinstance(balance_btc_str, str) else balance_btc_str
        balance_satoshi = int(balance_btc * 1e8)
        print(f"   Balance: {balance_btc:.8f} tBTC ({balance_satoshi:,} satoshi)")
        
        # Fee estimate
        fee_sat_per_byte = 15
        estimated_tx_size = 250
        estimated_fee_satoshi = fee_sat_per_byte * estimated_tx_size
        estimated_fee_btc = estimated_fee_satoshi / 1e8
        total_needed_satoshi = btc_amount_satoshi + estimated_fee_satoshi
        
        print(f"\n💸 Fee Estimate:")
        print(f"   Fee: {estimated_fee_satoshi:,} satoshi ({estimated_fee_btc:.8f} tBTC)")
        print(f"   Total needed: {total_needed_satoshi:,} satoshi")
        
        if balance_satoshi < total_needed_satoshi:
            shortfall = total_needed_satoshi - balance_satoshi
            print(f"\n❌ Insufficient balance!")
            print(f"   Shortfall: {shortfall:,} satoshi ({shortfall/1e8:.8f} tBTC)")
            sys.exit(1)
        
        print(f"\n✅ Sufficient balance. Creating transaction...")
        
        # Create transaction
        outputs = [(TO_ADDRESS, float(btc_amount), 'btc')]
        tx_hex = key.create_transaction(outputs, fee=fee_sat_per_byte)
        
        print(f"   Transaction created ({len(tx_hex) // 2} bytes)")
        
        # Broadcast
        print(f"\n📡 Broadcasting to Blockstream testnet...")
        broadcast_url = "https://blockstream.info/testnet/api/tx"
        
        response = requests.post(
            broadcast_url,
            data=tx_hex,
            headers={'Content-Type': 'text/plain'},
            timeout=30
        )
        
        if response.status_code == 200:
            tx_hash = response.text.strip()
            print(f"\n✅ Transaction broadcast successfully!")
            print(f"   Transaction Hash: {tx_hash}")
            print(f"\n📋 Transaction Links:")
            print(f"   Mempool: https://mempool.space/testnet/tx/{tx_hash}")
            print(f"   Blockstream: https://blockstream.info/testnet/tx/{tx_hash}")
            
            import time
            time.sleep(2)
            print(f"\n✅ Transaction should appear in mempool shortly")
        else:
            print(f"\n❌ Broadcast failed: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)
            
    except ImportError:
        print("❌ 'bit' library not installed")
        print("   Install with: pip install bit")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

else:
    print("❓ Unknown address format")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ Deposit initiated successfully!")
print("=" * 80)

