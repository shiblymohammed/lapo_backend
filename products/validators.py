"""Validators for product-related models"""
from django.core.exceptions import ValidationError
import os
import hashlib

# Try to import magic, but make it optional for Windows development
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False
    import warnings
    warnings.warn("python-magic not available. File type validation will be limited.")


def validate_image_file(file):
    """Validate image file format and size with enhanced security checks"""
    # Import PIL at function level to reduce initial memory footprint
    from PIL import Image
    
    # Check file size (max 5MB)
    max_size_mb = 5
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'Image file size cannot exceed {max_size_mb}MB.')
    
    # Check file extension
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f'Invalid file extension. Allowed: {", ".join(valid_extensions)}')
    
    # Validate MIME type using python-magic (if available)
    if MAGIC_AVAILABLE:
        try:
            file.seek(0)
            mime = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)
            
            allowed_mimes = ['image/jpeg', 'image/png', 'image/gif']
            if mime not in allowed_mimes:
                raise ValidationError(f'Invalid file type. Detected: {mime}. Allowed: {", ".join(allowed_mimes)}')
        except Exception as e:
            raise ValidationError(f'Error validating file type: {str(e)}')
    
    # Validate that it's actually an image using PIL
    try:
        img = Image.open(file)
        img.verify()
        
        # Check image format
        if img.format.upper() not in ['JPEG', 'PNG', 'GIF']:
            raise ValidationError('Invalid image format. Allowed: JPEG, PNG, GIF')
        
        # Re-open for dimension check (verify() closes the file)
        file.seek(0)
        img = Image.open(file)
        
        # Check for reasonable dimensions (prevent decompression bombs)
        max_pixels = 89_478_485  # PIL's default MAX_IMAGE_PIXELS
        if img.width * img.height > max_pixels:
            raise ValidationError('Image dimensions too large. Maximum pixels: 89,478,485')
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f'Invalid image file: {str(e)}')
    
    # Reset file pointer after reading
    file.seek(0)
    
    return file


def validate_document_file(file, allowed_extensions=None, max_size_mb=20):
    """Validate document file format and size with security checks"""
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.docx', '.doc']
    
    # Check file size
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'Document file size cannot exceed {max_size_mb}MB.')
    
    # Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f'Invalid file extension. Allowed: {", ".join(allowed_extensions)}')
    
    # Validate MIME type using python-magic (if available)
    if MAGIC_AVAILABLE:
        try:
            file.seek(0)
            mime = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)
            
            # Map extensions to expected MIME types (with common variations)
            mime_map = {
                '.pdf': ['application/pdf', 'application/x-pdf'],
                '.docx': [
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/zip'  # DOCX files are ZIP archives
                ],
                '.doc': ['application/msword', 'application/x-msword'],
            }
            
            expected_mimes = []
            for allowed_ext in allowed_extensions:
                expected_mimes.extend(mime_map.get(allowed_ext, []))
            
            # Also check if it's a generic binary/octet-stream (common for uploads)
            if mime not in expected_mimes and mime not in ['application/octet-stream', 'binary/octet-stream']:
                # Log the detected MIME type for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Unexpected MIME type for {file.name}: {mime}. Expected one of: {expected_mimes}')
                
                # For PDFs, check the file signature directly
                file.seek(0)
                header = file.read(5)
                file.seek(0)
                
                if ext == '.pdf' and header == b'%PDF-':
                    # It's a valid PDF based on signature, allow it
                    pass
                else:
                    raise ValidationError(f'Invalid file type. Detected: {mime}. Expected: {", ".join(expected_mimes)}')
        except ValidationError:
            raise
        except Exception as e:
            # Log the error but don't fail validation if MIME detection fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error validating file type for {file.name}: {str(e)}')
            
            # Fall back to basic signature check for PDFs
            if ext == '.pdf':
                try:
                    file.seek(0)
                    header = file.read(5)
                    file.seek(0)
                    if header != b'%PDF-':
                        raise ValidationError('Invalid PDF file signature')
                except Exception:
                    raise ValidationError(f'Error validating file: {str(e)}')
    
    # Check for malicious content patterns
    file.seek(0)
    content_sample = file.read(8192)  # Read first 8KB
    file.seek(0)
    
    # Check for executable signatures
    malicious_signatures = [
        b'MZ',  # DOS/Windows executable
        b'\x7fELF',  # Linux executable
        b'#!',  # Script shebang
        b'<?php',  # PHP script
        b'<script',  # JavaScript
    ]
    
    for signature in malicious_signatures:
        if signature in content_sample:
            raise ValidationError('File contains potentially malicious content')
    
    # Reset file pointer
    file.seek(0)
    
    return file


def validate_dynamic_resource_file(file, field_type, max_size_mb=None, allowed_extensions=None):
    """Validate files for dynamic resource submissions"""
    if field_type == 'image':
        # Use stricter size limit if specified
        if max_size_mb and max_size_mb < 5:
            if file.size > max_size_mb * 1024 * 1024:
                raise ValidationError(f'Image file size cannot exceed {max_size_mb}MB.')
        return validate_image_file(file)
    
    elif field_type == 'document':
        return validate_document_file(file, allowed_extensions, max_size_mb or 20)
    
    else:
        raise ValidationError(f'Unsupported field type for file validation: {field_type}')


def scan_file_for_malware(file):
    """
    Basic malware scanning using file signatures and patterns.
    In production, integrate with ClamAV or similar antivirus solution.
    """
    file.seek(0)
    
    # Read file header
    header = file.read(512)
    file.seek(0)
    
    # Check for common malware signatures
    suspicious_patterns = [
        b'MZ\x90\x00',  # PE executable
        b'\x7fELF',  # ELF executable
        b'PK\x03\x04',  # ZIP archive (could contain executables)
    ]
    
    # For images and documents, ZIP signature is expected in some formats
    # So we need context-aware checking
    file_ext = os.path.splitext(file.name)[1].lower()
    
    # ZIP is OK for .docx but not for images
    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
        for pattern in suspicious_patterns:
            if header.startswith(pattern):
                raise ValidationError('File contains suspicious executable content')
    
    # Check file hash against known malware (placeholder for real implementation)
    # In production, integrate with VirusTotal API or similar service
    file.seek(0)
    file_hash = hashlib.sha256(file.read()).hexdigest()
    file.seek(0)
    
    # Placeholder: In production, check hash against malware database
    # known_malware_hashes = get_malware_hashes()
    # if file_hash in known_malware_hashes:
    #     raise ValidationError('File matches known malware signature')
    
    return True


def optimize_image(image_file, max_width=1920, max_height=1920, quality=85):
    """Optimize image size while maintaining quality"""
    # Import PIL at function level to reduce initial memory footprint
    from PIL import Image
    from io import BytesIO
    
    try:
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Resize if image is too large
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = BytesIO()
        
        # Determine format
        format_map = {
            'JPEG': 'JPEG',
            'JPG': 'JPEG',
            'PNG': 'PNG',
            'GIF': 'GIF'
        }
        
        original_format = img.format if img.format else 'JPEG'
        save_format = format_map.get(original_format.upper(), 'JPEG')
        
        # Save with optimization
        if save_format == 'JPEG':
            img.save(output, format=save_format, quality=quality, optimize=True)
        elif save_format == 'PNG':
            img.save(output, format=save_format, optimize=True)
        else:
            img.save(output, format=save_format)
        
        output.seek(0)
        return output
        
    except Exception as e:
        raise ValidationError(f'Error optimizing image: {str(e)}')
