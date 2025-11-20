#!/usr/bin/env python
"""
Fix the address format issue and send $10 USD deposit.
"""
import os
import sys
import django
import requests
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import DepositAddress
from wallet.utils import reserve_next_index, create_deposit_address
from wallet.exchange_rates import get_exchange_rate

WIF_KEY = "cVn9pUq3bLWadJZ4JZVLoGPWnxZ1Pg5ayZ35yX5KGPRrFwrygHqW"
TARGET_ADDRESS = "bc1qqkc4eel5ujd6vexturqrtnn2pnhtep0yqsz0p0"
USD_AMOUNT = 10.0

print("=" * 80)
print("FIXING ADDRESS AND SENDING $10 USD DEPOSIT")
print("=" * 80)
print()

# Find the deposit address - try by address first, then by user if address was updated
deposit_addr = DepositAddress.objects.filter(address=TARGET_ADDRESS).first()

# If not found, try to find by user email (newtest@example.com based on earlier check)
if not deposit_addr:
    print(f"Address {TARGET_ADDRESS} not found - checking if it was updated...")
    # Try to find by user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.filter(email='newtest@example.com').first()
    if user:
        deposit_addr = DepositAddress.objects.filter(user=user, index=22).first()
        if deposit_addr:
            print(f"✅ Found address by user/index: {deposit_addr.address}")
            TARGET_ADDRESS = deposit_addr.address

if not deposit_addr:
    print(f"❌ Address not found in system")
    print(f"   Searched for: {TARGET_ADDRESS}")
    print(f"   Please verify the address exists in the database")
    sys.exit(1)

print(f"✅ Found deposit address:")
print(f"   User: {deposit_addr.user.email}")
print(f"   Network: {deposit_addr.network.name}")
print(f"   Current address: {deposit_addr.address}")
print(f"   Index: {deposit_addr.index}")
print()

# Check if address format is wrong
if deposit_addr.address.startswith('bc1') and deposit_addr.network.effective_is_testnet:
    print("⚠️  Address has 'bc1' prefix but network is testnet!")
    print("   This is incorrect - testnet bech32 should start with 'tb1'")
    print()
    print("Attempting to derive correct testnet address...")
    
    try:
        # Try to derive the correct address
        from wallet.utils import derive_address_from_xpub
        from django.conf import settings
        
        # Get xpub from network or settings
        xpub = deposit_addr.network.xpub or getattr(settings, 'DEFAULT_XPUB', '')
        if not xpub:
            # Try to get from environment
            import os
            xpub = os.getenv('DEFAULT_XPUB', '')
        
        if not xpub:
            raise ValueError("No xpub configured")
        
        correct_addr = derive_address_from_xpub(
            xpub,
            deposit_addr.index,
            deposit_addr.network.key,
            deposit_addr.network.effective_is_testnet
        )
        
        if correct_addr and correct_addr.startswith('tb1'):
            print(f"✅ Correct testnet address: {correct_addr}")
            print()
            print("Updating database with correct address...")
            deposit_addr.address = correct_addr
            deposit_addr.save()
            print(f"✅ Address updated in database")
            TARGET_ADDRESS = correct_addr
        else:
            print(f"⚠️  Derived address: {correct_addr}")
            print("   Address format still doesn't match expected testnet format")
            print("   Proceeding with original address...")
    except Exception as e:
        print(f"⚠️  Could not derive correct address: {e}")
        print("   Proceeding with address as-is...")
        print("   Note: Transaction may fail due to network mismatch")

print()
print("=" * 80)
print("SENDING DEPOSIT")
print("=" * 80)
print()

# Get exchange rate
print("📊 Fetching exchange rate...")
try:
    btc_rate = get_exchange_rate('BTC', 'USD')
    print(f"   Current BTC/USD rate: ${float(btc_rate):,.2f}")
except Exception as e:
    print(f"   ⚠️  Error: {e}")
    btc_rate = Decimal('50000.00')
    print(f"   Using fallback: ${float(btc_rate):,.2f}")

btc_amount = Decimal(str(USD_AMOUNT)) / btc_rate
btc_amount_satoshi = int(btc_amount * Decimal(10**8))

print(f"\n💰 Transaction Details:")
print(f"   Amount: ${USD_AMOUNT:.2f} USD")
print(f"   = {float(btc_amount):.8f} BTC")
print(f"   = {btc_amount_satoshi:,} satoshi")
print(f"   To: {TARGET_ADDRESS}")
print()

# Send using bit library
try:
    from bit import PrivateKeyTestnet
    
    print("🔑 Loading private key...")
    key = PrivateKeyTestnet(WIF_KEY)
    sender_address = key.address
    print(f"   Sender: {sender_address}")
    
    print(f"\n🔍 Checking balance...")
    # Check balance directly from Blockstream API (more reliable)
    try:
        balance_url = f"https://blockstream.info/testnet/api/address/{sender_address}"
        balance_response = requests.get(balance_url, timeout=10)
        if balance_response.status_code == 200:
            balance_data = balance_response.json()
            funded = balance_data.get('chain_stats', {}).get('funded_txo_sum', 0)
            spent = balance_data.get('chain_stats', {}).get('spent_txo_sum', 0)
            balance_satoshi = funded - spent
            balance_btc = balance_satoshi / 1e8
            print(f"   Balance: {balance_btc:.8f} tBTC ({balance_satoshi:,} satoshi)")
        else:
            # Fallback to bit library
            print(f"   ⚠️  Blockstream API returned {balance_response.status_code}, trying bit library...")
            balance_btc_str = key.get_balance()
            balance_btc = float(balance_btc_str) if isinstance(balance_btc_str, str) else balance_btc_str
            balance_satoshi = int(balance_btc * 1e8)
            print(f"   Balance: {balance_btc:.8f} tBTC ({balance_satoshi:,} satoshi)")
    except Exception as e:
        print(f"   ⚠️  Error checking balance via API: {e}")
        print(f"   Trying bit library...")
        try:
            balance_btc_str = key.get_balance()
            balance_btc = float(balance_btc_str) if isinstance(balance_btc_str, str) else balance_btc_str
            balance_satoshi = int(balance_btc * 1e8)
            print(f"   Balance: {balance_btc:.8f} tBTC ({balance_satoshi:,} satoshi)")
        except Exception as e2:
            print(f"   ❌ Could not check balance: {e2}")
            print(f"   Using previous balance check: 67,983 satoshi (from earlier check)")
            balance_satoshi = 67983
            balance_btc = balance_satoshi / 1e8
    
    # Fee estimate
    fee_sat_per_byte = 15
    estimated_tx_size = 250
    estimated_fee_satoshi = fee_sat_per_byte * estimated_tx_size
    total_needed_satoshi = btc_amount_satoshi + estimated_fee_satoshi
    
    print(f"\n💸 Fee Estimate:")
    print(f"   Fee: {estimated_fee_satoshi:,} satoshi")
    print(f"   Total needed: {total_needed_satoshi:,} satoshi")
    
    if balance_satoshi < total_needed_satoshi:
        shortfall = total_needed_satoshi - balance_satoshi
        print(f"\n❌ Insufficient balance!")
        print(f"   Shortfall: {shortfall:,} satoshi ({shortfall/1e8:.8f} tBTC)")
        sys.exit(1)
    
    print(f"\n✅ Sufficient balance. Creating transaction...")
    
    # Create transaction - use the address from database (may have been fixed)
    outputs = [(TARGET_ADDRESS, float(btc_amount), 'btc')]
    
    try:
        tx_hex = key.create_transaction(outputs, fee=fee_sat_per_byte)
        print(f"   ✅ Transaction created ({len(tx_hex) // 2} bytes)")
    except ValueError as e:
        if 'mainnet address' in str(e) or 'testnet address' in str(e):
            print(f"\n❌ Network mismatch error: {e}")
            print()
            print("The address format doesn't match the network.")
            print("This address may need to be corrected in the database.")
            print()
            print("To fix this, you can:")
            print("1. Derive the correct testnet address for this user/index")
            print("2. Update the deposit address in the database")
            print("3. Then retry the send")
            sys.exit(1)
        else:
            raise
    
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
        print(f"   The monitoring system will detect it automatically")
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

print("\n" + "=" * 80)
print("✅ Deposit initiated successfully!")
print("=" * 80)

