from django.core.management.base import BaseCommand
from authentication.models import CustomUser


class Command(BaseCommand):
    help = 'Create an admin user'

    def add_arguments(self, parser):
        parser.add_argument('phone', type=str, help='Phone number with country code (e.g., +919876543210)')
        parser.add_argument('--staff', action='store_true', help='Create staff user instead of admin')

    def handle(self, *args, **options):
        phone = options['phone']
        role = 'staff' if options['staff'] else 'admin'

        # Check if user already exists
        try:
            user = CustomUser.objects.get(phone_number=phone)
            user.role = role
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Updated existing user {phone} to {role}')
            )
        except CustomUser.DoesNotExist:
            # Create new user
            user = CustomUser.objects.create(
                username=phone,  # Use phone as username
                phone_number=phone,
                role=role,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created new {role} user: {phone}')
            )

        self.stdout.write(
            self.style.WARNING(f'\nUser will complete Firebase authentication on first login.')
        )
