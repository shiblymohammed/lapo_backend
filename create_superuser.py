#!/usr/bin/env python
"""
Create superuser automatically during deployment.
This script is safe to run multiple times - it won't create duplicates.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'election_cart.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Superuser credentials
USERNAME = 'aseeb'
PASSWORD = 'Dr.aseeb123'
EMAIL = 'aseeb@electioncart.com'

def create_superuser():
    """Create superuser if it doesn't exist."""
    try:
        if User.objects.filter(username=USERNAME).exists():
            user = User.objects.get(username=USERNAME)
            # Update role if it's not set to admin
            if user.role != 'admin':
                user.role = 'admin'
                user.save()
                print(f'✓ Updated "{USERNAME}" role to admin')
            else:
                print(f'✓ Superuser "{USERNAME}" already exists with admin role.')
            return
        
        user = User.objects.create_superuser(
            username=USERNAME,
            email=EMAIL,
            password=PASSWORD
        )
        # Set the role to 'admin' for the admin panel
        user.role = 'admin'
        user.save()
        
        print(f'✓ Superuser "{USERNAME}" created successfully!')
        print(f'  Username: {USERNAME}')
        print(f'  Email: {EMAIL}')
        print(f'  Role: admin')
        
    except Exception as e:
        print(f'✗ Error creating superuser: {e}')
        raise

if __name__ == '__main__':
    create_superuser()
