from django.contrib import admin
from .models import Package, PackageItem, Campaign, ProductAuditLog, ResourceFieldDefinition, ChecklistTemplateItem


class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 1


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'created_by', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PackageItemInline]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'unit', 'is_active', 'created_by', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProductAuditLog)
class ProductAuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'content_type', 'object_id', 'user']
    list_filter = ['action', 'content_type', 'timestamp']
    search_fields = ['object_id', 'user__username']
    readonly_fields = ['content_type', 'object_id', 'action', 'user', 'timestamp', 'changes']
    
    def has_add_permission(self, request):
        return False  # Audit logs should not be manually created
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should not be deleted



@admin.register(ResourceFieldDefinition)
class ResourceFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'field_type', 'content_type', 'object_id', 'is_required', 'order', 'created_at']
    list_filter = ['field_type', 'is_required', 'content_type']
    search_fields = ['field_name', 'help_text']
    readonly_fields = ['created_at']
    ordering = ['content_type', 'object_id', 'order']


@admin.register(ChecklistTemplateItem)
class ChecklistTemplateItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'content_type', 'object_id', 'order', 'is_optional', 'estimated_duration_minutes', 'created_at']
    list_filter = ['is_optional', 'content_type']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    ordering = ['content_type', 'object_id', 'order']
