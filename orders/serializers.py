from rest_framework import serializers
from .models import Order, OrderItem, OrderResource, OrderChecklist, ChecklistItem, DynamicResourceSubmission, PaymentHistory
from products.serializers import PackageSerializer, CampaignSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    item_type = serializers.SerializerMethodField()
    item_details = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'item_type', 'item_details', 'quantity', 'price', 'subtotal', 'resources_uploaded']
    
    def get_item_type(self, obj):
        """Return the type of item (package or campaign)"""
        return obj.content_type.model
    
    def get_item_details(self, obj):
        """Return serialized item details"""
        if obj.content_object:
            if obj.content_type.model == 'package':
                return PackageSerializer(obj.content_object).data
            elif obj.content_type.model == 'campaign':
                return CampaignSerializer(obj.content_object).data
        return None
    
    def get_subtotal(self, obj):
        """Return subtotal for this order item"""
        return float(obj.get_subtotal())


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    resource_upload_progress = serializers.SerializerMethodField()
    pending_resource_items = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    payment_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'total_amount', 'status', 'payment_status',
            'razorpay_order_id', 'razorpay_payment_id', 'payment_completed_at',
            'items', 'total_items', 'resource_upload_progress', 'pending_resource_items',
            'total_paid', 'payment_balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['order_number', 'razorpay_order_id', 'razorpay_payment_id']
    
    def get_total_items(self, obj):
        """Return total number of items"""
        return obj.get_total_items()
    
    def get_resource_upload_progress(self, obj):
        """Return resource upload progress percentage"""
        return obj.get_resource_upload_progress()
    
    def get_pending_resource_items(self, obj):
        """Return list of items that still need resources"""
        pending_items = []
        for item in obj.get_pending_resource_items():
            pending_items.append({
                'id': item.id,
                'item_type': item.content_type.model,
                'item_name': str(item.content_object) if item.content_object else 'Unknown',
                'quantity': item.quantity
            })
        return pending_items
    
    def get_total_paid(self, obj):
        """Return total amount paid"""
        return float(obj.get_total_paid())
    
    def get_payment_balance(self, obj):
        """Return remaining payment balance"""
        return float(obj.get_payment_balance())


class PaymentVerificationSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class OrderResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderResource
        fields = [
            'id', 'order_item', 'candidate_photo', 'party_logo',
            'campaign_slogan', 'preferred_date', 'whatsapp_number',
            'additional_notes', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_at']
    
    def validate_candidate_photo(self, value):
        """Validate candidate photo file"""
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError('File size cannot exceed 5MB')
        return value
    
    def validate_party_logo(self, value):
        """Validate party logo file"""
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError('File size cannot exceed 5MB')
        return value
    
    def validate_whatsapp_number(self, value):
        """Validate WhatsApp number"""
        cleaned_number = ''.join(filter(str.isdigit, value))
        if len(cleaned_number) < 10:
            raise serializers.ValidationError('WhatsApp number must be at least 10 digits')
        return value


class ResourceUploadSerializer(serializers.Serializer):
    """Serializer for uploading resources for a specific order item"""
    order_item_id = serializers.IntegerField()
    candidate_photo = serializers.ImageField()
    party_logo = serializers.ImageField()
    campaign_slogan = serializers.CharField(max_length=1000)
    preferred_date = serializers.DateField()
    whatsapp_number = serializers.CharField(max_length=15)
    additional_notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    
    def validate_candidate_photo(self, value):
        """Validate candidate photo file"""
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError('File size cannot exceed 5MB')
        return value
    
    def validate_party_logo(self, value):
        """Validate party logo file"""
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError('File size cannot exceed 5MB')
        return value
    
    def validate_whatsapp_number(self, value):
        """Validate WhatsApp number"""
        cleaned_number = ''.join(filter(str.isdigit, value))
        if len(cleaned_number) < 10:
            raise serializers.ValidationError('WhatsApp number must be at least 10 digits')
        return value


class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ['id', 'description', 'completed', 'completed_at', 'completed_by', 'order_index']


class OrderChecklistSerializer(serializers.ModelSerializer):
    items = ChecklistItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = OrderChecklist
        fields = ['id', 'order', 'items', 'created_at']



class DynamicResourceFieldSerializer(serializers.Serializer):
    """Serializer for dynamic resource field information"""
    id = serializers.IntegerField()
    field_name = serializers.CharField()
    field_type = serializers.CharField()
    is_required = serializers.BooleanField()
    order = serializers.IntegerField()
    help_text = serializers.CharField()
    max_file_size_mb = serializers.IntegerField(allow_null=True)
    max_length = serializers.IntegerField(allow_null=True)
    min_value = serializers.IntegerField(allow_null=True)
    max_value = serializers.IntegerField(allow_null=True)
    allowed_extensions = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class DynamicResourceSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for dynamic resource submissions"""
    field_definition = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    
    class Meta:
        model = DynamicResourceSubmission
        fields = ['id', 'field_definition', 'value', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_field_definition(self, obj):
        """Return field definition details"""
        return {
            'id': obj.field_definition.id,
            'field_name': obj.field_definition.field_name,
            'field_type': obj.field_definition.field_type,
        }
    
    def get_value(self, obj):
        """Return the appropriate value based on field type"""
        if obj.field_definition.field_type == 'text':
            return obj.text_value
        elif obj.field_definition.field_type == 'number':
            return obj.number_value
        elif obj.field_definition.field_type in ['image', 'document']:
            return obj.file_value.url if obj.file_value else None
        return None


class DynamicResourceSubmitSerializer(serializers.Serializer):
    """Serializer for submitting dynamic resources"""
    submissions = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
    
    def validate_submissions(self, value):
        """Validate that each submission has required fields"""
        for submission in value:
            if 'field_id' not in submission:
                raise serializers.ValidationError('Each submission must have a field_id')
            if 'value' not in submission:
                raise serializers.ValidationError('Each submission must have a value')
        return value


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'order_id', 'order_number', 'payment_method', 'transaction_id',
            'amount', 'currency', 'status', 'status_display', 'payment_date',
            'invoice_generated_at', 'invoice_number', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'invoice_generated_at', 'created_at']
