from rest_framework import serializers
from .models import Cart, CartItem
from products.serializers import PackageSerializer, CampaignSerializer


class CartItemSerializer(serializers.ModelSerializer):
    item_type = serializers.SerializerMethodField()
    item_details = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'item_type', 'item_details', 'quantity', 'subtotal', 'added_at']
    
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
        """Return subtotal for this cart item"""
        return float(obj.get_subtotal())


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'item_count', 'created_at', 'updated_at']
    
    def get_items(self, obj):
        """Return cart items, filtering out items with deleted products"""
        # Get all items and filter out those with null content_object
        valid_items = [item for item in obj.items.all() if item.content_object is not None]
        
        # Delete orphaned items (items with deleted products)
        orphaned_items = [item for item in obj.items.all() if item.content_object is None]
        for item in orphaned_items:
            item.delete()
        
        return CartItemSerializer(valid_items, many=True).data
    
    def get_total(self, obj):
        """Return total price of cart"""
        return float(obj.get_total())
    
    def get_item_count(self, obj):
        """Return number of items in cart"""
        return obj.get_item_count()


class AddToCartSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=['package', 'campaign'])
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
