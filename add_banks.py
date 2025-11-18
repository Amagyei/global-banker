#!/usr/bin/env python
"""
Add banks to the catalog.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from catalog.models import Country, Bank

# Banks to add (all US banks)
banks_to_add = [
    "Chime",
    "Align credit union",
    "Capital one",
    "Grow FCU",
    "Corning FCU",
    "Bank of America",
    "Scott credit Union",
]

def add_banks():
    """Add banks to the database."""
    # Get US country
    try:
        us_country = Country.objects.get(code='US')
    except Country.DoesNotExist:
        print("❌ US country not found. Please create it first.")
        return
    
    print(f"Adding banks to {us_country.name} ({us_country.code})...\n")
    
    added = 0
    skipped = 0
    
    for bank_name in banks_to_add:
        # Check if bank already exists
        existing = Bank.objects.filter(name__iexact=bank_name, country=us_country).first()
        if existing:
            print(f"⏭️  Skipped: {bank_name} (already exists)")
            skipped += 1
            continue
        
        # Create new bank
        bank = Bank.objects.create(
            name=bank_name,
            country=us_country,
            is_active=True
        )
        print(f"✅ Added: {bank_name} (ID: {bank.id})")
        added += 1
    
    print(f"\n{'=' * 50}")
    print(f"Summary:")
    print(f"  Added: {added}")
    print(f"  Skipped: {skipped}")
    print(f"  Total: {len(banks_to_add)}")
    print(f"{'=' * 50}")

if __name__ == '__main__':
    add_banks()

