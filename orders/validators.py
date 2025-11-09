"""Validators for order-related models"""
from django.core.exceptions import ValidationError
from products.validators import validate_dynamic_resource_file


def validate_dynamic_resource_submission(file, field_definition):
    """
    Validate file uploads for dynamic resource submissions.
    Uses field definition configuration for validation rules.
    """
    field_type = field_definition.field_type
    
    if field_type not in ['image', 'document']:
        raise ValidationError(f'File upload not supported for field type: {field_type}')
    
    # Get validation parameters from field definition
    max_size_mb = field_definition.max_file_size_mb
    allowed_extensions = field_definition.allowed_extensions if field_definition.allowed_extensions else None
    
    # Validate the file
    return validate_dynamic_resource_file(
        file=file,
        field_type=field_type,
        max_size_mb=max_size_mb,
        allowed_extensions=allowed_extensions
    )


def validate_whatsapp_number(value):
    """Validate WhatsApp number format"""
    if not value:
        return
    
    # Remove spaces and special characters
    cleaned_number = ''.join(filter(str.isdigit, value))
    
    if len(cleaned_number) < 10:
        raise ValidationError('WhatsApp number must be at least 10 digits')
    
    if len(cleaned_number) > 15:
        raise ValidationError('WhatsApp number cannot exceed 15 digits')
    
    return value
