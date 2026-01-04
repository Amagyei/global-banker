"""
Django management command to populate FullzPackage data
Run with: python manage.py populate_fullz_packages
"""
from django.core.management.base import BaseCommand
from catalog.models import Bank, FullzPackage


class Command(BaseCommand):
    help = 'Populate FullzPackage data for all active banks'

    def handle(self, *args, **options):
        # Get all active banks
        banks = Bank.objects.filter(is_active=True)

        if not banks.exists():
            self.stdout.write(self.style.WARNING('No active banks found. Please create banks first.'))
            return

        # Package templates - same names across all banks, but prices vary
        # Base prices (will be adjusted per bank)
        package_templates = [
            {
                'name': 'Starter Pack',
                'description': 'Perfect for beginners. Get started with a small bundle.',
                'quantity': 5,
                'base_price_minor': 5000,  # $50.00 base price
            },
            {
                'name': 'Standard Bundle',
                'description': 'Our most popular package. Great value for regular users.',
                'quantity': 10,
                'base_price_minor': 9000,  # $90.00 base price
            },
            {
                'name': 'Premium Package',
                'description': 'Best value! Get more fullz at a discounted rate.',
                'quantity': 25,
                'base_price_minor': 20000,  # $200.00 base price
            },
            {
                'name': 'Enterprise Bundle',
                'description': 'Maximum value for bulk buyers. Perfect for businesses.',
                'quantity': 50,
                'base_price_minor': 35000,  # $350.00 base price
            },
        ]

        # Price variation per bank (allows same package name, different prices)
        # Each bank gets a price variation factor (0.9 to 1.3 = -10% to +30%)
        import random
        random.seed(42)  # For consistent results
        
        # Create packages for each bank
        created_count = 0
        updated_count = 0
        
        # Store bank price factors to ensure consistency
        bank_factors = {}
        
        for bank in banks:
            # Generate a unique price variation for this bank (0.9 to 1.3)
            # This ensures same package names but different prices per bank
            if bank.id not in bank_factors:
                bank_factors[bank.id] = random.uniform(0.9, 1.3)
            bank_price_factor = bank_factors[bank.id]
            
            for template in package_templates:
                # Calculate price for this bank (base price * bank-specific factor)
                price_minor = int(template['base_price_minor'] * bank_price_factor)
                
                package, created = FullzPackage.objects.get_or_create(
                    bank=bank,
                    name=template['name'],
                    defaults={
                        'description': template['description'],
                        'quantity': template['quantity'],
                        'price_minor': price_minor,
                        'is_active': True,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created: {package}'))
                else:
                    # Update existing package if needed
                    updated = False
                    if package.description != template['description']:
                        package.description = template['description']
                        updated = True
                    if package.quantity != template['quantity']:
                        package.quantity = template['quantity']
                        updated = True
                    # Update price based on current bank's factor
                    # Compare Money amount to int (price_minor is MoneyField)
                    if int(package.price_minor.amount * 100) != price_minor:
                        package.price_minor = price_minor
                        updated = True
                    if updated:
                        package.save()
                        updated_count += 1
                        self.stdout.write(self.style.WARNING(f'Updated: {package}'))
                    else:
                        self.stdout.write(f'Already exists: {package}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Created {created_count} new packages, updated {updated_count} packages across {banks.count()} banks'
        ))
        self.stdout.write(self.style.SUCCESS(f'Total packages: {FullzPackage.objects.count()}'))

