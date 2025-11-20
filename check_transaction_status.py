#!/usr/bin/env python
"""Check if pending transactions match blockchain"""
import requests

# The two pending transaction hashes from earlier
pending_txs = [
    "448fda4e47ce21676c2265d999b3ac77da7e0d8927bd067fff",
    "499268e937431ca0b3485043420f32aff43a04811e68b2fa6e"
]

address = "n4V4qAwMjfzKfoZEXQ7pPxVaC7GywWEaUC"
base_url = "https://blockstream.info/testnet/api"

print("=" * 80)
print("CHECKING PENDING TRANSACTIONS ON BLOCKCHAIN")
print("=" * 80)
print()

for tx_hash in pending_txs:
    print(f"Transaction: {tx_hash}")
    print("-" * 80)
    
    try:
        # Get transaction details
        response = requests.get(f"{base_url}/tx/{tx_hash}", timeout=10)
        response.raise_for_status()
        tx = response.json()
        
        status = tx.get('status', {})
        confirmed = status.get('confirmed', False)
        block_height = status.get('block_height')
        block_time = status.get('block_time')
        
        # Get current block height for confirmations
        tip_response = requests.get(f"{base_url}/blocks/tip/height", timeout=5)
        current_height = int(tip_response.text)
        confirmations = current_height - block_height + 1 if block_height else 0
        
        print(f"  Status: {'✅ CONFIRMED' if confirmed else '⏳ PENDING'}")
        if confirmed:
            print(f"  Block Height: {block_height}")
            print(f"  Confirmations: {confirmations}")
            print(f"  Block Time: {block_time}")
        
        # Check if this transaction sent to our address
        vouts = [v for v in tx.get('vout', []) if v.get('scriptpubkey_address') == address]
        if vouts:
            total_received = sum(v.get('value', 0) for v in vouts)
            print(f"  Amount to {address[:20]}...: {total_received} satoshi ({total_received/100000000:.8f} BTC)")
            print(f"  ✅ Transaction successfully sent to address!")
        else:
            print(f"  ⚠️  This transaction does not send to {address}")
        
        print()
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()

print("=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("If both transactions show as CONFIRMED and send to the address,")
print("then YES, the transactions were successful!")
print("The monitoring system just needs to be run to update the status.")

