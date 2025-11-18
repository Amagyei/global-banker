#!/usr/bin/env python
"""
Send Bitcoin from a wallet to an address.
"""
import os
import sys
import django
import requests
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.exchange_rates import get_exchange_rate

def send_bitcoin(wif_key, to_address, usd_amount, network='testnet'):
    """
    Send Bitcoin using WIF private key.
    
    Args:
        wif_key: Wallet Import Format private key
        to_address: Destination Bitcoin address
        usd_amount: Amount in USD to send
        network: 'testnet' or 'mainnet'
    """
    print("=" * 70)
    print("BITCOIN TRANSACTION SENDER")
    print("=" * 70)
    
    # Get current BTC/USD rate
    print(f"\n📊 Fetching exchange rate...")
    try:
        btc_rate = get_exchange_rate('btc', 'usd')
        print(f"   Current BTC/USD rate: ${float(btc_rate):,.2f}")
    except Exception as e:
        print(f"   ❌ Error fetching rate: {e}")
        return
    
    # Calculate BTC amount
    btc_amount = Decimal(str(usd_amount)) / Decimal(str(btc_rate))
    print(f"\n💰 Transaction Details:")
    print(f"   Amount: ${usd_amount:.2f} USD")
    print(f"   = {float(btc_amount):.8f} BTC")
    print(f"   To: {to_address}")
    print(f"   Network: {network}")
    
    # Send Bitcoin using bit library
    try:
        if network == 'testnet':
            from bit import PrivateKeyTestnet
            
            # Create private key from WIF for testnet
            key = PrivateKeyTestnet(wif_key)
            sender_address = key.address
            
            print(f"\n🔍 Checking sender balance...")
            print(f"   Sender address: {sender_address}")
            
            # Get balance (returns in BTC as string or float)
            balance_btc_str = key.get_balance()
            balance_btc = float(balance_btc_str) if isinstance(balance_btc_str, str) else balance_btc_str
            print(f"   Balance: {balance_btc:.8f} tBTC")
            
            # Fee in satoshis per byte (testnet typically uses lower fees)
            fee_sat_per_byte = 15  # Conservative fee for testnet
            
            print(f"\n💸 Fee Estimate:")
            print(f"   Fee rate: {fee_sat_per_byte} sat/byte")
            
            # Estimate total needed (rough estimate: ~250 bytes for a simple transaction)
            estimated_tx_size = 250  # bytes
            estimated_fee_btc = Decimal(str((fee_sat_per_byte * estimated_tx_size) / 100000000))
            total_needed = btc_amount + estimated_fee_btc
            
            print(f"   Estimated fee: {estimated_fee_btc:.8f} tBTC")
            print(f"   Total needed: {float(total_needed):.8f} tBTC")
            
            if balance_btc < float(total_needed):
                print(f"\n❌ Insufficient balance!")
                print(f"   Have: {balance_btc:.8f} tBTC")
                print(f"   Need: {float(total_needed):.8f} tBTC")
                print(f"   Short: {float(total_needed) - balance_btc:.8f} tBTC")
                return
            
            print(f"\n📝 Transaction Summary:")
            print(f"   Amount: {float(btc_amount):.8f} tBTC to {to_address}")
            print(f"   Fee: {estimated_fee_btc:.8f} tBTC (estimated)")
            
            # Create and broadcast transaction
            print(f"\n🔨 Creating transaction...")
            
            # Define outputs: [(address, amount, unit)]
            outputs = [(to_address, float(btc_amount), 'btc')]
            
            # Create the transaction (returns hex string directly)
            tx_hex = key.create_transaction(outputs, fee=fee_sat_per_byte)
            
            print(f"   Transaction created: {len(tx_hex) // 2} bytes")
            print(f"   Transaction hex: {tx_hex[:60]}...")
            
            # Manually broadcast to Blockstream API to ensure it's broadcast
            print(f"\n📡 Broadcasting to Blockstream API...")
            broadcast_url = "https://blockstream.info/testnet/api/tx"
            
            # Blockstream API expects raw hex string as plain text
            try:
                response = requests.post(
                    broadcast_url,
                    data=tx_hex,
                    headers={'Content-Type': 'text/plain'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    tx_hash = response.text.strip()
                    print(f"\n✅ Transaction broadcast successfully to Blockstream!")
                    print(f"   Transaction ID: {tx_hash}")
                    
                    # Wait a moment for propagation
                    import time
                    print(f"   Waiting 2 seconds for propagation...")
                    time.sleep(2)
                    
                    # Verify it's in the mempool
                    print(f"\n🔍 Verifying broadcast...")
                    verify_url = f"https://blockstream.info/testnet/api/tx/{tx_hash}"
                    verify_response = requests.get(verify_url, timeout=10)
                    if verify_response.status_code == 200:
                        print(f"   ✅ Transaction confirmed in mempool!")
                        explorer_tx_url = f"https://mempool.space/testnet/tx/{tx_hash}"
                        print(f"   View on explorer: {explorer_tx_url}")
                        print(f"   Alternative: https://blockstream.info/testnet/tx/{tx_hash}")
                    else:
                        print(f"   ⚠️  Transaction broadcast but may take a moment to appear")
                        print(f"   Transaction ID: {tx_hash}")
                        print(f"   Check: https://blockstream.info/testnet/tx/{tx_hash}")
                else:
                    print(f"   ⚠️  Blockstream broadcast failed (status {response.status_code})")
                    print(f"   Response: {response.text}")
                    raise Exception(f"Blockstream API returned {response.status_code}: {response.text}")
            except Exception as broadcast_error:
                print(f"   ❌ Blockstream broadcast failed: {broadcast_error}")
                print(f"\n   Transaction hex (for manual broadcast):")
                print(f"   {tx_hex}")
                print(f"\n   You can manually broadcast this transaction using:")
                print(f"   curl -X POST https://blockstream.info/testnet/api/tx -H 'Content-Type: text/plain' -d '{tx_hex}'")
                raise
        else:
            from bit import PrivateKey
            
            # Create private key from WIF for mainnet
            key = PrivateKey(wif_key)
            sender_address = key.address
            
            print(f"\n🔍 Checking sender balance...")
            print(f"   Sender address: {sender_address}")
            
            # Get balance (returns in BTC as string or float)
            balance_btc_str = key.get_balance()
            balance_btc = float(balance_btc_str) if isinstance(balance_btc_str, str) else balance_btc_str
            print(f"   Balance: {balance_btc:.8f} BTC")
            
            # Fee in satoshis per byte (mainnet typically uses higher fees)
            fee_sat_per_byte = 50  # Conservative fee for mainnet
            
            print(f"\n💸 Fee Estimate:")
            print(f"   Fee rate: {fee_sat_per_byte} sat/byte")
            
            # Estimate total needed
            estimated_tx_size = 250  # bytes
            estimated_fee_btc = Decimal(str((fee_sat_per_byte * estimated_tx_size) / 100000000))
            total_needed = btc_amount + estimated_fee_btc
            
            print(f"   Estimated fee: {estimated_fee_btc:.8f} BTC")
            print(f"   Total needed: {float(total_needed):.8f} BTC")
            
            if balance_btc < float(total_needed):
                print(f"\n❌ Insufficient balance!")
                print(f"   Have: {balance_btc:.8f} BTC")
                print(f"   Need: {float(total_needed):.8f} BTC")
                print(f"   Short: {float(total_needed) - balance_btc:.8f} BTC")
                return
            
            print(f"\n📝 Transaction Summary:")
            print(f"   Amount: {float(btc_amount):.8f} BTC to {to_address}")
            print(f"   Fee: {estimated_fee_btc:.8f} BTC (estimated)")
            
            # Create and broadcast transaction
            print(f"\n🔨 Creating transaction...")
            
            outputs = [(to_address, float(btc_amount), 'btc')]
            
            # Create the transaction (returns hex string directly)
            tx_hex = key.create_transaction(outputs, fee=fee_sat_per_byte)
            
            print(f"   Transaction created: {len(tx_hex) // 2} bytes")
            print(f"   Transaction hex: {tx_hex[:60]}...")
            
            # Manually broadcast to Blockstream API to ensure it's broadcast
            print(f"\n📡 Broadcasting to Blockstream API...")
            broadcast_url = "https://blockstream.info/api/tx"
            
            # Blockstream API expects raw hex string as plain text
            try:
                response = requests.post(
                    broadcast_url,
                    data=tx_hex,
                    headers={'Content-Type': 'text/plain'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    tx_hash = response.text.strip()
                    print(f"\n✅ Transaction broadcast successfully to Blockstream!")
                    print(f"   Transaction ID: {tx_hash}")
                    
                    # Wait a moment for propagation
                    import time
                    print(f"   Waiting 2 seconds for propagation...")
                    time.sleep(2)
                    
                    # Verify it's in the mempool
                    print(f"\n🔍 Verifying broadcast...")
                    verify_url = f"https://blockstream.info/api/tx/{tx_hash}"
                    verify_response = requests.get(verify_url, timeout=10)
                    if verify_response.status_code == 200:
                        print(f"   ✅ Transaction confirmed in mempool!")
                        explorer_tx_url = f"https://mempool.space/tx/{tx_hash}"
                        print(f"   View on explorer: {explorer_tx_url}")
                        print(f"   Alternative: https://blockstream.info/tx/{tx_hash}")
                    else:
                        print(f"   ⚠️  Transaction broadcast but may take a moment to appear")
                        print(f"   Transaction ID: {tx_hash}")
                        print(f"   Check: https://blockstream.info/tx/{tx_hash}")
                else:
                    print(f"   ⚠️  Blockstream broadcast failed (status {response.status_code})")
                    print(f"   Response: {response.text}")
                    raise Exception(f"Blockstream API returned {response.status_code}: {response.text}")
            except Exception as broadcast_error:
                print(f"   ❌ Blockstream broadcast failed: {broadcast_error}")
                print(f"\n   Transaction hex (for manual broadcast):")
                print(f"   {tx_hex}")
                print(f"\n   You can manually broadcast this transaction using:")
                print(f"   curl -X POST https://blockstream.info/api/tx -H 'Content-Type: text/plain' -d '{tx_hex}'")
                raise
            
    except ImportError as e:
        print(f"\n❌ Missing required library: {e}")
        print(f"   Install with: pip install bit")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\nTroubleshooting Tips:")
        print(f" - Ensure your WIF key is correct and matches the network ({network})")
        print(f" - Check that the address has a confirmed balance greater than the amount + fee")
        print(f" - Try increasing the fee rate if the transaction fails to appear in the mempool")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Default values from user's request
    wif_key = "cVn9pUq3bLWadJZ4JZVLoGPWnxZ1Pg5ayZ35yX5KGPRrFwrygHqW"
    to_address = "tb1qtsgxt956r02czvtyqqq9tr4qvcc40s258nf5vu"
    usd_amount = 20.0
    network = 'testnet'  # Address starts with 'tb1' which is testnet
    
    if len(sys.argv) > 1:
        to_address = sys.argv[1]
    if len(sys.argv) > 2:
        usd_amount = float(sys.argv[2])
    if len(sys.argv) > 3:
        wif_key = sys.argv[3]
    
    send_bitcoin(wif_key, to_address, usd_amount, network)

