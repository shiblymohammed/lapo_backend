from django.core.management.base import BaseCommand
from products.models import Package, PackageItem, Campaign


class Command(BaseCommand):
    help = 'Populate database with sample packages and campaigns'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating products...')

        # Clear existing products
        Package.objects.all().delete()
        Campaign.objects.all().delete()

        # Create Packages
        election_hungama = Package.objects.create(
            name='Election Hungama',
            price=18500.00,
            description='Complete election campaign package with all essential materials and services for a comprehensive ward-level campaign.',
            is_active=True
        )

        PackageItem.objects.bulk_create([
            PackageItem(package=election_hungama, name='Posters (A3 size)', quantity=100),
            PackageItem(package=election_hungama, name='Pamphlets', quantity=500),
            PackageItem(package=election_hungama, name='Banners (6x4 ft)', quantity=5),
            PackageItem(package=election_hungama, name='Stickers', quantity=200),
            PackageItem(package=election_hungama, name='Social Media Campaign', quantity=1),
            PackageItem(package=election_hungama, name='WhatsApp Campaign', quantity=1),
        ])

        premium_package = Package.objects.create(
            name='Premium Campaign Package',
            price=35000.00,
            description='Premium election campaign package with enhanced visibility and comprehensive digital marketing support.',
            is_active=True
        )

        PackageItem.objects.bulk_create([
            PackageItem(package=premium_package, name='Posters (A3 size)', quantity=200),
            PackageItem(package=premium_package, name='Pamphlets', quantity=1000),
            PackageItem(package=premium_package, name='Banners (6x4 ft)', quantity=10),
            PackageItem(package=premium_package, name='Stickers', quantity=500),
            PackageItem(package=premium_package, name='Social Media Campaign (Premium)', quantity=1),
            PackageItem(package=premium_package, name='WhatsApp Campaign', quantity=1),
            PackageItem(package=premium_package, name='Video Campaign', quantity=1),
            PackageItem(package=premium_package, name='Door-to-Door Campaign Support', quantity=1),
        ])

        starter_package = Package.objects.create(
            name='Starter Campaign Package',
            price=1.00,
            description='Budget-friendly starter package perfect for small ward campaigns and first-time candidates.',
            is_active=True
        )

        PackageItem.objects.bulk_create([
            PackageItem(package=starter_package, name='Posters (A3 size)', quantity=50),
            PackageItem(package=starter_package, name='Pamphlets', quantity=250),
            PackageItem(package=starter_package, name='Banners (6x4 ft)', quantity=2),
            PackageItem(package=starter_package, name='Stickers', quantity=100),
            PackageItem(package=starter_package, name='Social Media Posts', quantity=10),
        ])

        # Create Campaigns
        Campaign.objects.create(
            name='Coffee with Candidate',
            price=10000.00,
            unit='Per Ward',
            description='Organize an intimate coffee meeting with voters to discuss issues and build personal connections. Includes venue setup, refreshments, and promotional materials.',
            is_active=True
        )

        Campaign.objects.create(
            name='Door-to-Door Campaign',
            price=15000.00,
            unit='Per Ward',
            description='Comprehensive door-to-door campaign service with trained volunteers to reach every household in your ward. Includes campaign materials and volunteer coordination.',
            is_active=True
        )

        Campaign.objects.create(
            name='Social Media Blitz',
            price=8000.00,
            unit='Per Month',
            description='Intensive social media campaign across Facebook, Instagram, and Twitter. Includes content creation, daily posts, and engagement management.',
            is_active=True
        )

        Campaign.objects.create(
            name='WhatsApp Campaign',
            price=5000.00,
            unit='Per Ward',
            description='Targeted WhatsApp campaign reaching voters through group messages, status updates, and personalized messages. Includes message design and scheduling.',
            is_active=True
        )

        Campaign.objects.create(
            name='Street Corner Meetings',
            price=12000.00,
            unit='Per Ward',
            description='Organize multiple street corner meetings to connect with voters in their neighborhoods. Includes sound system, stage setup, and promotional materials.',
            is_active=True
        )

        Campaign.objects.create(
            name='Video Campaign Production',
            price=20000.00,
            unit='Per Video',
            description='Professional video production for campaign advertisements. Includes scripting, shooting, editing, and distribution across digital platforms.',
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS('Successfully populated products!'))
        self.stdout.write(f'Created {Package.objects.count()} packages')
        self.stdout.write(f'Created {Campaign.objects.count()} campaigns')
