"""Management command to set up secure file storage directories"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import stat


class Command(BaseCommand):
    help = 'Set up secure file storage directories with proper permissions'
    
    def handle(self, *args, **options):
        """Create secure storage directories with proper permissions"""
        
        # Get secure media root
        secure_media_root = settings.SECURE_MEDIA_ROOT
        
        # Define directory structure
        directories = [
            'products/images',
            'products/thumbnails',
            'resources/dynamic',
            'resources/orders',
            'invoices',
        ]
        
        self.stdout.write(f"Setting up secure storage at: {secure_media_root}")
        
        # Create base directory
        if not os.path.exists(secure_media_root):
            os.makedirs(secure_media_root, mode=0o750)
            self.stdout.write(self.style.SUCCESS(f"✓ Created base directory: {secure_media_root}"))
        else:
            self.stdout.write(f"Base directory already exists: {secure_media_root}")
        
        # Create subdirectories
        for directory in directories:
            dir_path = os.path.join(secure_media_root, directory)
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, mode=0o750)
                self.stdout.write(self.style.SUCCESS(f"✓ Created directory: {directory}"))
            else:
                self.stdout.write(f"Directory already exists: {directory}")
            
            # Set permissions
            try:
                os.chmod(dir_path, 0o750)  # rwxr-x---
                self.stdout.write(f"  Set permissions: 750 (rwxr-x---)")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Could not set permissions: {e}"))
        
        # Create .htaccess file to prevent direct web access (for Apache)
        htaccess_path = os.path.join(secure_media_root, '.htaccess')
        if not os.path.exists(htaccess_path):
            with open(htaccess_path, 'w') as f:
                f.write("# Deny all direct access\n")
                f.write("Deny from all\n")
            os.chmod(htaccess_path, 0o640)
            self.stdout.write(self.style.SUCCESS("✓ Created .htaccess file"))
        
        # Create nginx.conf snippet (for reference)
        nginx_conf_path = os.path.join(secure_media_root, 'nginx.conf.example')
        if not os.path.exists(nginx_conf_path):
            with open(nginx_conf_path, 'w') as f:
                f.write("# Nginx configuration to deny direct access\n")
                f.write("# Add this to your nginx server block:\n\n")
                f.write(f"location {secure_media_root} {{\n")
                f.write("    deny all;\n")
                f.write("    return 404;\n")
                f.write("}\n")
            os.chmod(nginx_conf_path, 0o640)
            self.stdout.write(self.style.SUCCESS("✓ Created nginx.conf.example"))
        
        # Create README
        readme_path = os.path.join(secure_media_root, 'README.md')
        if not os.path.exists(readme_path):
            with open(readme_path, 'w') as f:
                f.write("# Secure Media Storage\n\n")
                f.write("This directory contains user-uploaded files that should NOT be directly accessible via web URLs.\n\n")
                f.write("## Security Measures\n\n")
                f.write("1. **Location**: Files are stored outside the web root\n")
                f.write("2. **Permissions**: Directories have 750 (rwxr-x---) permissions\n")
                f.write("3. **File Permissions**: Files have 640 (rw-r-----) permissions\n")
                f.write("4. **Access Control**: Files are served through Django views with authentication\n")
                f.write("5. **Web Server**: Configure .htaccess (Apache) or nginx.conf (Nginx) to deny direct access\n\n")
                f.write("## Directory Structure\n\n")
                f.write("- `products/images/` - Product images organized by date\n")
                f.write("- `products/thumbnails/` - Generated thumbnails\n")
                f.write("- `resources/dynamic/` - User-uploaded dynamic resources\n")
                f.write("- `resources/orders/` - Order-specific resources\n")
                f.write("- `invoices/` - Generated invoice PDFs\n\n")
                f.write("## Maintenance\n\n")
                f.write("- Regularly backup this directory\n")
                f.write("- Monitor disk usage\n")
                f.write("- Implement file retention policies\n")
                f.write("- Scan for malware periodically\n")
            os.chmod(readme_path, 0o640)
            self.stdout.write(self.style.SUCCESS("✓ Created README.md"))
        
        self.stdout.write(self.style.SUCCESS("\n✓ Secure storage setup complete!"))
        self.stdout.write("\nNext steps:")
        self.stdout.write("1. Configure your web server to deny direct access to this directory")
        self.stdout.write("2. Set up regular backups")
        self.stdout.write("3. Implement file retention policies")
        self.stdout.write("4. Consider integrating antivirus scanning")
