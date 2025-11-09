"""
Management command to migrate existing images to Cloudinary
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from products.models import ProductImage
from orders.models import DynamicResourceSubmission, OrderResource
import cloudinary.uploader
import os


class Command(BaseCommand):
    help = 'Migrate existing local images to Cloudinary'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )
        parser.add_argument(
            '--delete-local',
            action='store_true',
            help='Delete local files after successful upload',
        )
    
    def handle(self, *args, **options):
        if not settings.USE_CLOUDINARY:
            self.stdout.write(self.style.ERROR(
                'Cloudinary is not configured. Please set CLOUDINARY_* environment variables.'
            ))
            return
        
        dry_run = options['dry_run']
        delete_local = options['delete_local']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Migrate product images
        self.stdout.write(self.style.SUCCESS('\n=== Migrating Product Images ==='))
        self.migrate_product_images(dry_run, delete_local)
        
        # Migrate user resources
        self.stdout.write(self.style.SUCCESS('\n=== Migrating User Resources ==='))
        self.migrate_user_resources(dry_run, delete_local)
        
        # Migrate order resources
        self.stdout.write(self.style.SUCCESS('\n=== Migrating Order Resources ==='))
        self.migrate_order_resources(dry_run, delete_local)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Migration complete!'))
    
    def migrate_product_images(self, dry_run, delete_local):
        """Migrate ProductImage records"""
        images = ProductImage.objects.all()
        total = images.count()
        
        self.stdout.write(f'Found {total} product images to migrate')
        
        for i, image in enumerate(images, 1):
            if not image.image:
                continue
            
            try:
                # Check if already on Cloudinary
                if 'cloudinary.com' in image.image.url:
                    self.stdout.write(f'[{i}/{total}] Already on Cloudinary: {image.id}')
                    continue
                
                if dry_run:
                    self.stdout.write(f'[{i}/{total}] Would migrate: {image.image.name}')
                    continue
                
                # Upload to Cloudinary
                self.stdout.write(f'[{i}/{total}] Uploading: {image.image.name}')
                
                result = cloudinary.uploader.upload(
                    image.image.path,
                    folder='products/images',
                    resource_type='image',
                    quality='auto',
                    fetch_format='auto'
                )
                
                # Update image field with Cloudinary URL
                image.image = result['secure_url']
                image.save()
                
                self.stdout.write(self.style.SUCCESS(f'✓ Uploaded: {result["secure_url"]}'))
                
                # Delete local file if requested
                if delete_local and os.path.exists(image.image.path):
                    os.remove(image.image.path)
                    self.stdout.write(f'  Deleted local file')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error migrating {image.id}: {str(e)}'))
    
    def migrate_user_resources(self, dry_run, delete_local):
        """Migrate DynamicResourceSubmission files"""
        submissions = DynamicResourceSubmission.objects.filter(file_value__isnull=False)
        total = submissions.count()
        
        self.stdout.write(f'Found {total} user resources to migrate')
        
        for i, submission in enumerate(submissions, 1):
            if not submission.file_value:
                continue
            
            try:
                # Check if already on Cloudinary
                if 'cloudinary.com' in submission.file_value.url:
                    self.stdout.write(f'[{i}/{total}] Already on Cloudinary: {submission.id}')
                    continue
                
                if dry_run:
                    self.stdout.write(f'[{i}/{total}] Would migrate: {submission.file_value.name}')
                    continue
                
                # Upload to Cloudinary
                self.stdout.write(f'[{i}/{total}] Uploading: {submission.file_value.name}')
                
                # Determine resource type
                ext = os.path.splitext(submission.file_value.name)[1].lower()
                resource_type = 'image' if ext in ['.jpg', '.jpeg', '.png', '.gif'] else 'raw'
                
                result = cloudinary.uploader.upload(
                    submission.file_value.path,
                    folder='user_resources/dynamic',
                    resource_type=resource_type,
                    quality='auto' if resource_type == 'image' else None,
                    fetch_format='auto' if resource_type == 'image' else None
                )
                
                # Update file field
                submission.file_value = result['secure_url']
                submission.save()
                
                self.stdout.write(self.style.SUCCESS(f'✓ Uploaded: {result["secure_url"]}'))
                
                # Delete local file if requested
                if delete_local and os.path.exists(submission.file_value.path):
                    os.remove(submission.file_value.path)
                    self.stdout.write(f'  Deleted local file')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error migrating {submission.id}: {str(e)}'))
    
    def migrate_order_resources(self, dry_run, delete_local):
        """Migrate OrderResource images"""
        resources = OrderResource.objects.all()
        total = resources.count()
        
        self.stdout.write(f'Found {total} order resources to migrate')
        
        for i, resource in enumerate(resources, 1):
            try:
                # Migrate candidate photo
                if resource.candidate_photo and 'cloudinary.com' not in resource.candidate_photo.url:
                    if dry_run:
                        self.stdout.write(f'[{i}/{total}] Would migrate candidate photo: {resource.candidate_photo.name}')
                    else:
                        self.stdout.write(f'[{i}/{total}] Uploading candidate photo')
                        result = cloudinary.uploader.upload(
                            resource.candidate_photo.path,
                            folder='user_resources/photos',
                            resource_type='image',
                            quality='auto',
                            fetch_format='auto'
                        )
                        resource.candidate_photo = result['secure_url']
                        self.stdout.write(self.style.SUCCESS(f'✓ Uploaded candidate photo'))
                
                # Migrate party logo
                if resource.party_logo and 'cloudinary.com' not in resource.party_logo.url:
                    if dry_run:
                        self.stdout.write(f'[{i}/{total}] Would migrate party logo: {resource.party_logo.name}')
                    else:
                        self.stdout.write(f'[{i}/{total}] Uploading party logo')
                        result = cloudinary.uploader.upload(
                            resource.party_logo.path,
                            folder='user_resources/logos',
                            resource_type='image',
                            quality='auto',
                            fetch_format='auto'
                        )
                        resource.party_logo = result['secure_url']
                        self.stdout.write(self.style.SUCCESS(f'✓ Uploaded party logo'))
                
                if not dry_run:
                    resource.save()
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error migrating order resource {resource.id}: {str(e)}'))
