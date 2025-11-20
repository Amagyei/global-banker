#!/usr/bin/env python
"""
Script to check OXA Pay payment status and manually trigger webhook processing
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from wallet.models import OxaPayPayment
from wallet.webhooks import process_paid_payment, process_failed_payment, process_expired_payment
from django.utils import timezone
import json

def check_payment(address_or_track_id):
    """Check payment status and provide diagnostic information"""
    
    # Try to find by address first, then track_id
    payment = None
    if address_or_track_id.startswith('T') or address_or_track_id.startswith('0x') or address_or_track_id.startswith('bc1'):
        # Looks like an address
        payment = OxaPayPayment.objects.filter(address=address_or_track_id).first()
    else:
        # Looks like a track_id
        payment = OxaPayPayment.objects.filter(track_id=address_or_track_id).first()
    
    if not payment:
        print(f"❌ No payment found with address/track_id: {address_or_track_id}")
        return
    
    print("=" * 80)
    print("OXA Pay Payment Status Check")
    print("=" * 80)
    print(f"Track ID: {payment.track_id}")
    print(f"Address: {payment.address}")
    print(f"Status: {payment.status}")
    print(f"Amount: {payment.amount} {payment.currency.upper()}")
    print(f"Pay Amount: {payment.pay_amount} {payment.pay_currency.upper() if payment.pay_amount else 'N/A'}")
    print(f"User: {payment.user.email}")
    print(f"Created: {payment.created_at}")
    print(f"Updated: {payment.updated_at}")
    print(f"Expired At: {payment.expired_at}")
    print()
    
    # Check expiration
    if payment.expired_at:
        is_expired = timezone.now() > payment.expired_at
        print(f"Expiration Status: {'❌ EXPIRED' if is_expired else '✅ Still Valid'}")
        if is_expired:
            print(f"  Expired at: {payment.expired_at}")
            print(f"  Current time: {timezone.now()}")
            print("  ⚠️  WARNING: This payment address has expired!")
            print("     OXA Pay will not process payments to expired addresses.")
        print()
    
    # Show raw response
    print("OXA Pay Response Data:")
    print("-" * 80)
    print(json.dumps(payment.raw_response, indent=2))
    print()
    
    # Diagnostic information
    print("Diagnostic Information:")
    print("-" * 80)
    print(f"1. Payment Status: {payment.status}")
    print(f"   - 'pending': Waiting for payment or confirmation")
    print(f"   - 'paid': Payment confirmed and credited")
    print(f"   - 'failed': Payment failed")
    print(f"   - 'expired': Payment expired")
    print()
    
    print("2. Why payment might not show in OXA Pay account:")
    print("   a) Payment expired (addresses expire after 60 minutes)")
    print("   b) Webhook not received (OXA Pay needs to detect payment on blockchain)")
    print("   c) Payment still confirming (needs blockchain confirmations)")
    print("   d) Amount mismatch (sent amount doesn't match expected amount)")
    print("   e) Network mismatch (payment sent to wrong network)")
    print()
    
    print("3. How to verify:")
    print(f"   - Check blockchain: https://tronscan.org/#/address/{payment.address}")
    print(f"   - Check OXA Pay dashboard for track_id: {payment.track_id}")
    print("   - Check webhook logs for callbacks from OXA Pay")
    print("   - Verify payment was sent to correct TRON address (starts with 'T')")
    print()
    
    # Check if there's a transaction hash
    if hasattr(payment, 'tx_hash') and payment.tx_hash:
        print(f"4. Transaction Hash: {payment.tx_hash}")
        print(f"   - Check on blockchain: https://tronscan.org/#/transaction/{payment.tx_hash}")
    else:
        print("4. Transaction Hash: None (payment not yet confirmed)")
    print()
    
    # Check related top-up intent
    if payment.topup_intent:
        print("5. Related Top-Up Intent:")
        print(f"   - ID: {payment.topup_intent.id}")
        print(f"   - Status: {payment.topup_intent.status}")
        print(f"   - Amount: ${payment.topup_intent.amount_minor / 100:.2f} USD")
    print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_oxapay_payment.py <address_or_track_id>")
        print("Example: python check_oxapay_payment.py TXfsCNFo9MpASgWgQofqp6YS1hZpXbH1GH")
        print("Example: python check_oxapay_payment.py 157800141")
        sys.exit(1)
    
    check_payment(sys.argv[1])

