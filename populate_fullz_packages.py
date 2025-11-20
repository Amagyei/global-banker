#!/usr/bin/env python
"""
Script to populate FullzPackage data for testing
Run with: python manage.py shell < populate_fullz_packages.py
Or: python manage.py shell
>>> exec(open('populate_fullz_packages.py').read())
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_banker.settings')
django.setup()

from catalog.models import Bank, FullzPackage

# Get all active banks
banks = Bank.objects.filter(is_active=True)

# Package templates
package_templates = [
    {
        'name': 'Starter Pack',
        'description': 'Perfect for beginners. Get started with a small bundle.',
        'quantity': 5,
        'price_minor': 5000,  # $50.00
    },
    {
        'name': 'Standard Bundle',
        'description': 'Our most popular package. Great value for regular users.',
        'quantity': 10,
        'price_minor': 9000,  # $90.00
    },
    {
        'name': 'Premium Package',
        'description': 'Best value! Get more fullz at a discounted rate.',
        'quantity': 25,
        'price_minor': 20000,  # $200.00
    },
    {
        'name': 'Enterprise Bundle',
        'description': 'Maximum value for bulk buyers. Perfect for businesses.',
        'quantity': 50,
        'price_minor': 35000,  # $350.00
    },
]

# Create packages for each bank
created_count = 0
for bank in banks:
    for template in package_templates:
        package, created = FullzPackage.objects.get_or_create(
            bank=bank,
            name=template['name'],
            defaults={
                'description': template['description'],
                'quantity': template['quantity'],
                'price_minor': template['price_minor'],
                'is_active': True,
            }
        )
        if created:
            created_count += 1
            print(f"Created: {package}")
        else:
            print(f"Already exists: {package}")

print(f"\n✅ Created {created_count} new packages across {banks.count()} banks")
print(f"Total packages: {FullzPackage.objects.count()}")

