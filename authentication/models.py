from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    
    DISTRICT_CHOICES = [
        ('thiruvananthapuram', 'Thiruvananthapuram'),
        ('kollam', 'Kollam'),
        ('pathanamthitta', 'Pathanamthitta'),
        ('alappuzha', 'Alappuzha'),
        ('kottayam', 'Kottayam'),
        ('idukki', 'Idukki'),
        ('ernakulam', 'Ernakulam'),
        ('thrissur', 'Thrissur'),
        ('palakkad', 'Palakkad'),
        ('malappuram', 'Malappuram'),
        ('kozhikode', 'Kozhikode'),
        ('wayanad', 'Wayanad'),
        ('kannur', 'Kannur'),
        ('kasaragod', 'Kasaragod'),
    ]
    
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    firebase_uid = models.CharField(max_length=128, unique=True, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    
    # Location fields for manual orders
    panchayath = models.CharField(max_length=100, blank=True, null=True, help_text='Panchayath/Municipality name')
    district = models.CharField(max_length=50, choices=DISTRICT_CHOICES, blank=True, null=True, help_text='District in Kerala')
    ward_number = models.CharField(max_length=10, blank=True, null=True, help_text='Ward number')
    notes = models.TextField(blank=True, null=True, help_text='Additional notes about the customer')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} ({self.role})"
