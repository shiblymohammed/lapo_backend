from django.core.management.base import BaseCommand
from authentication.models import CustomUser


class Command(BaseCommand):
    help = 'Create test staff members for development'

    def handle(self, *args, **kwargs):
        # Create staff members with different name configurations
        staff_data = [
            {
                'username': 'staff1',
                'phone_number': '+919876543210',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'role': 'staff',
                'email': 'rajesh.kumar@example.com'
            },
            {
                'username': 'staff2',
                'phone_number': '+919876543211',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'role': 'staff',
                'email': 'priya.sharma@example.com'
            },
            {
                'username': 'staff3',
                'phone_number': '+919876543212',
                'first_name': 'Amit',
                'last_name': '',
                'role': 'staff',
                'email': 'amit@example.com'
            },
            {
                'username': 'staff4',
                'phone_number': '+919876543213',
                'first_name': '',
                'last_name': 'Singh',
                'role': 'staff',
                'email': 'singh@example.com'
            },
            {
                'username': 'staff5',
                'phone_number': '+919876543214',
                'first_name': '',
                'last_name': '',
                'role': 'staff',
                'email': 'staff5@example.com'
            },
        ]

        created_count = 0
        updated_count = 0

        for data in staff_data:
            user, created = CustomUser.objects.update_or_create(
                phone_number=data['phone_number'],
                defaults={
                    'username': data['username'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': data['role'],
                    'email': data['email']
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created staff member: {user.phone_number} - {user.first_name} {user.last_name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated staff member: {user.phone_number} - {user.first_name} {user.last_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSummary: {created_count} created, {updated_count} updated')
        )
