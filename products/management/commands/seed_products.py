from django.core.management.base import BaseCommand
from products.models import Package, PackageItem, Campaign


class Command(BaseCommand):
    help = 'Seed initial package and campaign data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding products data...')
        
        # Clear existing data
        PackageItem.objects.all().delete()
        Package.objects.all().delete()
        Campaign.objects.all().delete()
        
        # Create Election Hungama Package
        election_hungama = Package.objects.create(
            name='Election Hungama',
            price=18500.00,
            description='Complete election campaign package with digital tools and promotional materials',
            is_active=True
        )
        
        # Add items to Election Hungama package
        package_items = [
            {'name': 'Ward Level App', 'quantity': 1},
            {'name': 'AI Intro Videos', 'quantity': 1},
            {'name': 'Digital Printer', 'quantity': 1},
        ]
        
        for item_data in package_items:
            PackageItem.objects.create(
                package=election_hungama,
                **item_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created package: {election_hungama.name}'))
        
        # Create Campaigns
        campaigns_data = [
            {
                'name': 'Coffee with Candidate',
                'price': 10000.00,
                'unit': 'Per Ward',
                'description': 'Interactive coffee session with voters to connect personally with the candidate'
            },
            {
                'name': 'Vision in VR',
                'price': 15000.00,
                'unit': 'Per Ward',
                'description': 'Virtual reality experience showcasing the candidate\'s vision and development plans'
            },
            {
                'name': 'Podcast Live Studio',
                'price': 12000.00,
                'unit': 'Per Ward',
                'description': 'Professional podcast recording setup for live discussions and voter engagement'
            },
            {
                'name': 'Health ATM',
                'price': 8000.00,
                'unit': 'Per Ward',
                'description': 'Mobile health checkup kiosk providing basic health services to voters'
            },
        ]
        
        for campaign_data in campaigns_data:
            campaign = Campaign.objects.create(**campaign_data, is_active=True)
            self.stdout.write(self.style.SUCCESS(f'Created campaign: {campaign.name}'))
        
        self.stdout.write(self.style.SUCCESS('\nSeeding completed successfully!'))
        self.stdout.write(f'Total packages: {Package.objects.count()}')
        self.stdout.write(f'Total campaigns: {Campaign.objects.count()}')
