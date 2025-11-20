#!/usr/bin/env python
"""Check balance of a Bitcoin testnet address"""
import requests
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.exchange_rates import get_exchange_rate, convert_crypto_to_usd
from decimal import Decimal

def check_address_balance(address):
    """Check balance of a Bitcoin testnet address using Blockstream API"""
    
    # Blockstream testnet API
    base_url = "https://blockstream.info/testnet/api"
    
    print(f"Checking balance for address: {address}")
    print(f"Network: Bitcoin Testnet")
    print("-" * 80)
    
    try:
        # Get address info
        response = requests.get(f"{base_url}/address/{address}", timeout=10)
        response.raise_for_status()
        address_info = response.json()
        
        # Get address transactions
        response = requests.get(f"{base_url}/address/{address}/txs", timeout=10)
        response.raise_for_status()
        transactions = response.json()
        
        # Calculate balance
        funded = address_info.get('chain_stats', {}).get('funded_txo_sum', 0)
        spent = address_info.get('chain_stats', {}).get('spent_txo_sum', 0)
        balance_satoshi = funded - spent
        
        # Also check mempool (unconfirmed)
        mempool_funded = address_info.get('mempool_stats', {}).get('funded_txo_sum', 0)
        mempool_spent = address_info.get('mempool_stats', {}).get('spent_txo_sum', 0)
        mempool_balance = mempool_funded - mempool_spent
        
        # Convert to BTC
        balance_btc = Decimal(balance_satoshi) / Decimal(10**8)
        mempool_btc = Decimal(mempool_balance) / Decimal(10**8)
        
        # Get USD value
        btc_rate = get_exchange_rate('BTC', 'USD')
        balance_usd = float(balance_btc) * float(btc_rate)
        mempool_usd = float(mempool_btc) * float(btc_rate)
        
        print(f"\n📊 BALANCE INFORMATION:")
        print(f"  Confirmed Balance: {balance_btc:.8f} BTC (${balance_usd:.2f} USD)")
        print(f"  Unconfirmed (Mempool): {mempool_btc:.8f} BTC (${mempool_usd:.2f} USD)")
        print(f"  Total Balance: {(balance_btc + mempool_btc):.8f} BTC (${balance_usd + mempool_usd:.2f} USD)")
        
        print(f"\n📈 STATISTICS:")
        print(f"  Total Received: {Decimal(funded) / Decimal(10**8):.8f} BTC")
        print(f"  Total Sent: {Decimal(spent) / Decimal(10**8):.8f} BTC")
        print(f"  Transaction Count: {address_info.get('chain_stats', {}).get('tx_count', 0)}")
        
        print(f"\n🔗 RECENT TRANSACTIONS:")
        if transactions:
            for i, tx in enumerate(transactions[:5], 1):
                txid = tx.get('txid', 'unknown')
                status = tx.get('status', {})
                confirmed = status.get('confirmed', False)
                block_height = status.get('block_height')
                confirmations = 'N/A'
                if confirmed and block_height:
                    # Get current block height
                    try:
                        tip_response = requests.get(f"{base_url}/blocks/tip/height", timeout=5)
                        current_height = int(tip_response.text)
                        confirmations = current_height - block_height + 1
                    except:
                        confirmations = '?'
                
                print(f"  {i}. {txid[:50]}...")
                print(f"     Status: {'Confirmed' if confirmed else 'Pending'}")
                if confirmed:
                    print(f"     Confirmations: {confirmations}")
                    print(f"     Block Height: {block_height}")
        else:
            print("  No transactions found")
        
        return {
            'address': address,
            'balance_satoshi': balance_satoshi,
            'balance_btc': float(balance_btc),
            'balance_usd': balance_usd,
            'mempool_balance_btc': float(mempool_btc),
            'mempool_balance_usd': mempool_usd,
            'tx_count': address_info.get('chain_stats', {}).get('tx_count', 0)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching address data: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test address from user
    address = "n4V4qAwMjfzKfoZEXQ7pPxVaC7GywWEaUC"
    
    print("=" * 80)
    print("BITCOIN TESTNET ADDRESS BALANCE CHECKER")
    print("=" * 80)
    print()
    
    result = check_address_balance(address)
    
    if result:
        print("\n" + "=" * 80)
        print("✅ Balance check completed successfully")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Balance check failed")
        print("=" * 80)

