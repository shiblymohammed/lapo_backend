from django.core.management.base import BaseCommand
from authentication.models import CustomUser


class Command(BaseCommand):
    help = 'Create test users for development'

    def handle(self, *args, **kwargs):
        # Create admin user
        if not CustomUser.objects.filter(username='admin').exists():
            admin = CustomUser.objects.create_user(
                username='admin',
                password='admin123',
                phone_number='+919111111111',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user: admin / admin123'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))

        # Create staff user
        if not CustomUser.objects.filter(username='staff').exists():
            staff = CustomUser.objects.create_user(
                username='staff',
                password='staff123',
                phone_number='+919222222222',
                role='staff'
            )
            self.stdout.write(self.style.SUCCESS(f'Created staff user: staff / staff123'))
        else:
            self.stdout.write(self.style.WARNING('Staff user already exists'))

        # Create regular user
        if not CustomUser.objects.filter(username='user').exists():
            user = CustomUser.objects.create_user(
                username='user',
                password='user123',
                phone_number='+919333333333',
                role='user'
            )
            self.stdout.write(self.style.SUCCESS(f'Created regular user: user / user123'))
        else:
            self.stdout.write(self.style.WARNING('Regular user already exists'))

        self.stdout.write(self.style.SUCCESS('\nTest users created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nYou can now login with:'))
        self.stdout.write('  Admin: username=admin, password=admin123')
        self.stdout.write('  Staff: username=staff, password=staff123')
        self.stdout.write('  User: username=user, password=user123')
