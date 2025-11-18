#!/usr/bin/env python
"""
Check balance for a specific Bitcoin wallet address.
"""
import os
import sys
import django
import requests
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import DepositAddress, OnChainTransaction
from wallet.blockchain import BlockchainMonitor
from wallet.exchange_rates import get_exchange_rate
from django.conf import settings

def check_address_balance(address):
    """Check balance for a specific Bitcoin address."""
    print("=" * 70)
    print("BITCOIN WALLET BALANCE CHECKER")
    print("=" * 70)
    print(f"\nAddress: {address}")
    
    # Detect network from address prefix
    if address.startswith('n') or address.startswith('m') or address.startswith('2') or address.startswith('tb1'):
        is_testnet = True
        network_name = "Testnet"
        explorer_url = "https://blockstream.info/testnet/api"
        explorer_web = "https://blockstream.info/testnet"
    elif address.startswith('1') or address.startswith('3') or address.startswith('bc1'):
        is_testnet = False
        network_name = "Mainnet"
        explorer_url = "https://blockstream.info/api"
        explorer_web = "https://blockstream.info"
    else:
        print(f"\n⚠️  Unknown address format. Assuming testnet.")
        is_testnet = True
        network_name = "Testnet"
        explorer_url = "https://blockstream.info/testnet/api"
        explorer_web = "https://blockstream.info/testnet"
    
    print(f"Network: {network_name}")
    print(f"Explorer: {explorer_web}/address/{address}")
    
    # Check if address exists in our database
    db_address = DepositAddress.objects.filter(address=address).first()
    if db_address:
        print(f"\n✅ Address found in database")
        print(f"   User: {db_address.user.email if db_address.user else 'N/A'}")
        print(f"   Network: {db_address.network.name}")
        print(f"   Index: {db_address.index}")
        print(f"   Created: {db_address.created_at}")
        
        # Check on-chain transactions in database
        db_txs = OnChainTransaction.objects.filter(to_address=address)
        if db_txs.exists():
            print(f"\n📊 Database Transactions: {db_txs.count()}")
            for tx in db_txs.order_by('-occurred_at'):
                print(f"   {tx.tx_hash[:30]}... - {tx.amount_atomic / (10 ** db_address.network.decimals):.8f} BTC")
                print(f"     Status: {tx.status} ({tx.confirmations}/{tx.required_confirmations} confirmations)")
    else:
        print(f"\nℹ️  Address not found in database (external wallet)")
    
    # Check blockchain directly
    print(f"\n🔍 Checking blockchain...")
    try:
        # Use Blockstream Esplora API
        api_url = f"{explorer_url}/address/{address}"
        
        # Get address info
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        addr_info = response.json()
        
        # Get transactions
        txs_url = f"{api_url}/txs"
        txs_response = requests.get(txs_url, timeout=10)
        txs_response.raise_for_status()
        txs = txs_response.json()
        
        # Calculate balance
        # For testnet, we need to sum all received amounts
        total_received = Decimal('0')
        total_sent = Decimal('0')
        
        if isinstance(txs, list):
            for tx in txs:
                # Check if this address received coins in this transaction
                for vout in tx.get('vout', []):
                    scriptpubkey_address = vout.get('scriptpubkey_address')
                    if scriptpubkey_address == address:
                        amount_sat = vout.get('value', 0)
                        total_received += Decimal(str(amount_sat)) / Decimal('100000000')  # Convert satoshi to BTC
                
                # Check if this address sent coins in this transaction
                for vin in tx.get('vin', []):
                    prev_tx = vin.get('prevout', {})
                    if prev_tx.get('scriptpubkey_address') == address:
                        amount_sat = prev_tx.get('value', 0)
                        total_sent += Decimal(str(amount_sat)) / Decimal('100000000')
        
        balance_btc = total_received - total_sent
        
        print(f"\n💰 Balance Information:")
        print(f"   Total Received: {total_received:.8f} BTC")
        print(f"   Total Sent:     {total_sent:.8f} BTC")
        print(f"   Current Balance: {balance_btc:.8f} BTC")
        
        # Convert to USD if we have exchange rate
        try:
            btc_rate = get_exchange_rate('btc', 'usd')
            balance_usd = float(balance_btc) * float(btc_rate)
            print(f"   ≈ ${balance_usd:.2f} USD (at ${float(btc_rate):,.2f}/BTC)")
        except Exception as e:
            print(f"   (Could not fetch USD rate: {e})")
        
        # Show transaction count
        if isinstance(txs, list):
            print(f"\n📊 Transaction History:")
            print(f"   Total transactions: {len(txs)}")
            
            if len(txs) > 0:
                print(f"\n   Recent transactions:")
                for tx in txs[:5]:
                    tx_hash = tx.get('txid', 'unknown')
                    confirmations = tx.get('status', {}).get('block_height', 0)
                    if confirmations:
                        confirmations = addr_info.get('chain_stats', {}).get('funded_txo_count', 0)  # Approximate
                    print(f"   • {tx_hash[:30]}... ({len(tx.get('vout', []))} outputs)")
        
        # Show address stats if available
        if isinstance(addr_info, dict):
            chain_stats = addr_info.get('chain_stats', {})
            mempool_stats = addr_info.get('mempool_stats', {})
            
            funded = chain_stats.get('funded_txo_sum', 0) / 100000000
            spent = chain_stats.get('spent_txo_sum', 0) / 100000000
            tx_count = chain_stats.get('tx_count', 0)
            
            print(f"\n📈 Address Statistics:")
            print(f"   Total funded: {funded:.8f} BTC")
            print(f"   Total spent:  {spent:.8f} BTC")
            print(f"   Transaction count: {tx_count}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error checking blockchain: {e}")
        print(f"   URL attempted: {api_url}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        # Default to the address from user's message
        address = "n4V4qAwMjfzKfoZEXQ7pPxVaC7GywWEaUC"
    
    check_address_balance(address)

