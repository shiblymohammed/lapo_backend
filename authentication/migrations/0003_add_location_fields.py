# Generated migration for adding location fields to CustomUser

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_alter_customuser_firebase_uid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='panchayath',
            field=models.CharField(blank=True, help_text='Panchayath/Municipality name', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='district',
            field=models.CharField(blank=True, choices=[('thiruvananthapuram', 'Thiruvananthapuram'), ('kollam', 'Kollam'), ('pathanamthitta', 'Pathanamthitta'), ('alappuzha', 'Alappuzha'), ('kottayam', 'Kottayam'), ('idukki', 'Idukki'), ('ernakulam', 'Ernakulam'), ('thrissur', 'Thrissur'), ('palakkad', 'Palakkad'), ('malappuram', 'Malappuram'), ('kozhikode', 'Kozhikode'), ('wayanad', 'Wayanad'), ('kannur', 'Kannur'), ('kasaragod', 'Kasaragod')], help_text='District in Kerala', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='ward_number',
            field=models.CharField(blank=True, help_text='Ward number', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='notes',
            field=models.TextField(blank=True, help_text='Additional notes about the customer', null=True),
        ),
    ]
