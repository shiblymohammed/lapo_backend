from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q, Prefetch
from .models import Package, Campaign, ChecklistTemplateItem, ProductAuditLog, ProductImage
from .serializers import (
    PackageSerializer, CampaignSerializer, ChecklistTemplateItemSerializer,
    PackageWriteSerializer, CampaignWriteSerializer, ProductListSerializer,
    ProductAuditLogSerializer, ProductImageSerializer, ProductImageWriteSerializer
)
from orders.models import Order, OrderItem


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing packages.
    Provides list and detail endpoints.
    """
    queryset = Package.objects.filter(is_active=True).prefetch_related('items')
    serializer_class = PackageSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular packages (max 3)"""
        popular_packages = Package.objects.filter(
            is_active=True,
            is_popular=True
        ).prefetch_related('items').order_by('popular_order', '-created_at')[:3]
        
        serializer = self.get_serializer(popular_packages, many=True)
        return Response(serializer.data)


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing campaigns.
    Provides list and detail endpoints.
    """
    queryset = Campaign.objects.filter(is_active=True)
    serializer_class = CampaignSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular campaigns (max 3)"""
        popular_campaigns = Campaign.objects.filter(
            is_active=True,
            is_popular=True
        ).order_by('popular_order', '-created_at')[:3]
        
        serializer = self.get_serializer(popular_campaigns, many=True)
        return Response(serializer.data)


class ChecklistTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing checklist template items for products.
    Admin-only access.
    """
    serializer_class = ChecklistTemplateItemSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Filter checklist items by product type and ID"""
        product_type = self.kwargs.get('product_type')
        product_id = self.kwargs.get('product_id')
        
        if product_type and product_id:
            # Get the content type for the product
            if product_type == 'package':
                content_type = ContentType.objects.get_for_model(Package)
            elif product_type == 'campaign':
                content_type = ContentType.objects.get_for_model(Campaign)
            else:
                return ChecklistTemplateItem.objects.none()
            
            return ChecklistTemplateItem.objects.filter(
                content_type=content_type,
                object_id=product_id
            )
        
        return ChecklistTemplateItem.objects.all()
    
    def list(self, request, *args, **kwargs):
        """List checklist template items for a product"""
        product_type = kwargs.get('product_type')
        product_id = kwargs.get('product_id')
        
        if not product_type or not product_id:
            return Response(
                {'error': 'Product type and ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify product exists
        if product_type == 'package':
            get_object_or_404(Package, id=product_id)
        elif product_type == 'campaign':
            get_object_or_404(Campaign, id=product_id)
        else:
            return Response(
                {'error': 'Invalid product type. Must be "package" or "campaign"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new checklist template item for a product"""
        product_type = kwargs.get('product_type')
        product_id = kwargs.get('product_id')
        
        if not product_type or not product_id:
            return Response(
                {'error': 'Product type and ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the product
        if product_type == 'package':
            product = get_object_or_404(Package, id=product_id)
            content_type = ContentType.objects.get_for_model(Package)
        elif product_type == 'campaign':
            product = get_object_or_404(Campaign, id=product_id)
            content_type = ContentType.objects.get_for_model(Campaign)
        else:
            return Response(
                {'error': 'Invalid product type. Must be "package" or "campaign"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the checklist template item
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # If order is not provided, set it to the next available order
        if 'order' not in request.data or request.data['order'] is None:
            max_order = ChecklistTemplateItem.objects.filter(
                content_type=content_type,
                object_id=product.id
            ).aggregate(models.Max('order'))['order__max']
            order = (max_order or 0) + 1
            serializer.save(content_type=content_type, object_id=product.id, order=order)
        else:
            serializer.save(content_type=content_type, object_id=product.id)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update a checklist template item"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a checklist template item"""
        instance = self.get_object()
        instance.delete()
        return Response(
            {'message': 'Checklist template item deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['patch'], url_path='reorder')
    def reorder(self, request, *args, **kwargs):
        """Reorder checklist template items"""
        items_order = request.data.get('items', [])
        
        if not items_order:
            return Response(
                {'error': 'Items array is required with format: [{"id": 1, "order": 0}, ...]'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that all items exist and belong to the same product
        item_ids = [item.get('id') for item in items_order if item.get('id') is not None]
        items = ChecklistTemplateItem.objects.filter(id__in=item_ids)
        
        if items.count() != len(item_ids):
            return Response(
                {'error': 'One or more checklist items not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update the order for each item
        updated_items = []
        for item_data in items_order:
            item_id = item_data.get('id')
            new_order = item_data.get('order')
            
            if item_id is not None and new_order is not None:
                ChecklistTemplateItem.objects.filter(id=item_id).update(order=new_order)
                updated_items.append(item_id)
        
        # Return updated items
        updated_queryset = ChecklistTemplateItem.objects.filter(id__in=updated_items).order_by('order')
        serializer = self.get_serializer(updated_queryset, many=True)
        return Response({
            'message': f'Successfully reordered {len(updated_items)} items',
            'items': serializer.data
        })



def create_audit_log(product, action, user, changes=None):
    """Helper function to create audit log entries"""
    content_type = ContentType.objects.get_for_model(product)
    ProductAuditLog.objects.create(
        content_type=content_type,
        object_id=product.id,
        action=action,
        user=user,
        changes=changes or {}
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_all_products(request):
    """
    List all products (packages and campaigns) in a unified format.
    Supports search by name and filtering by type.
    """
    search_query = request.query_params.get('search', '')
    product_type = request.query_params.get('type', '')  # 'package' or 'campaign'
    
    products = []
    
    # Get packages
    if not product_type or product_type == 'package':
        packages = Package.objects.select_related('created_by').all()
        if search_query:
            packages = packages.filter(name__icontains=search_query)
        
        for package in packages:
            products.append({
                'id': package.id,
                'name': package.name,
                'price': package.price,
                'description': package.description,
                'is_active': package.is_active,
                'is_popular': package.is_popular,
                'popular_order': package.popular_order,
                'created_at': package.created_at,
                'updated_at': package.updated_at,
                'created_by_name': package.created_by.get_full_name() if package.created_by else 'N/A',
                'type': 'package'
            })
    
    # Get campaigns
    if not product_type or product_type == 'campaign':
        campaigns = Campaign.objects.select_related('created_by').all()
        if search_query:
            campaigns = campaigns.filter(name__icontains=search_query)
        
        for campaign in campaigns:
            products.append({
                'id': campaign.id,
                'name': campaign.name,
                'price': campaign.price,
                'description': campaign.description,
                'is_active': campaign.is_active,
                'is_popular': campaign.is_popular,
                'popular_order': campaign.popular_order,
                'created_at': campaign.created_at,
                'updated_at': campaign.updated_at,
                'created_by_name': campaign.created_by.get_full_name() if campaign.created_by else 'N/A',
                'type': 'campaign'
            })
    
    # Sort by created_at descending
    products.sort(key=lambda x: x['created_at'], reverse=True)
    
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_package(request):
    """Create a new package"""
    serializer = PackageWriteSerializer(data=request.data)
    
    if serializer.is_valid():
        package = serializer.save(created_by=request.user)
        
        # Create audit log
        create_audit_log(package, 'create', request.user, {
            'name': package.name,
            'price': str(package.price)
        })
        
        # Return full package data
        response_serializer = PackageSerializer(package, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_campaign(request):
    """Create a new campaign"""
    serializer = CampaignWriteSerializer(data=request.data)
    
    if serializer.is_valid():
        campaign = serializer.save(created_by=request.user)
        
        # Create audit log
        create_audit_log(campaign, 'create', request.user, {
            'name': campaign.name,
            'price': str(campaign.price)
        })
        
        # Return full campaign data
        response_serializer = CampaignSerializer(campaign, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_product_detail(request, product_type, product_id):
    """Get details of a specific product"""
    if product_type == 'package':
        product = get_object_or_404(Package, id=product_id)
        serializer = PackageSerializer(product, context={'request': request})
    elif product_type == 'campaign':
        product = get_object_or_404(Campaign, id=product_id)
        serializer = CampaignSerializer(product, context={'request': request})
    else:
        return Response(
            {'error': 'Invalid product type. Must be "package" or "campaign"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_product(request, product_type, product_id):
    """Update a product"""
    if product_type == 'package':
        product = get_object_or_404(Package, id=product_id)
        old_data = {
            'name': product.name,
            'price': str(product.price),
            'is_active': product.is_active
        }
        serializer = PackageWriteSerializer(product, data=request.data)
    elif product_type == 'campaign':
        product = get_object_or_404(Campaign, id=product_id)
        old_data = {
            'name': product.name,
            'price': str(product.price),
            'is_active': product.is_active
        }
        serializer = CampaignWriteSerializer(product, data=request.data)
    else:
        return Response(
            {'error': 'Invalid product type. Must be "package" or "campaign"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if serializer.is_valid():
        updated_product = serializer.save()
        
        # Track changes
        new_data = {
            'name': updated_product.name,
            'price': str(updated_product.price),
            'is_active': updated_product.is_active
        }
        changes = {k: {'old': old_data[k], 'new': new_data[k]} 
                   for k in old_data if old_data[k] != new_data[k]}
        
        # Create audit log
        create_audit_log(updated_product, 'update', request.user, changes)
        
        # Return full product data
        if product_type == 'package':
            response_serializer = PackageSerializer(updated_product, context={'request': request})
        else:
            response_serializer = CampaignSerializer(updated_product, context={'request': request})
        
        return Response(response_serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_product(request, product_type, product_id):
    """Delete a product"""
    if product_type == 'package':
        product = get_object_or_404(Package, id=product_id)
        content_type = ContentType.objects.get_for_model(Package)
    elif product_type == 'campaign':
        product = get_object_or_404(Campaign, id=product_id)
        content_type = ContentType.objects.get_for_model(Campaign)
    else:
        return Response(
            {'error': 'Invalid product type. Must be "package" or "campaign"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if product has pending or in-progress orders
    active_orders = OrderItem.objects.filter(
        content_type=content_type,
        object_id=product_id,
        order__status__in=['pending_payment', 'pending_resources', 'ready_for_processing', 'assigned', 'in_progress']
    ).exists()
    
    if active_orders:
        return Response(
            {'error': 'Cannot delete product with pending or in-progress orders. Please deactivate it instead.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create audit log before deletion
    product_name = product.name
    create_audit_log(product, 'delete', request.user, {
        'name': product_name,
        'deleted_at': str(models.functions.Now())
    })
    
    # Delete the product
    product.delete()
    
    return Response(
        {'message': f'{product_type.capitalize()} deleted successfully'},
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def toggle_product_status(request, product_type, product_id):
    """Toggle product active status"""
    if product_type == 'package':
        product = get_object_or_404(Package, id=product_id)
    elif product_type == 'campaign':
        product = get_object_or_404(Campaign, id=product_id)
    else:
        return Response(
            {'error': 'Invalid product type. Must be "package" or "campaign"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Toggle status
    old_status = product.is_active
    product.is_active = not product.is_active
    product.save()
    
    # Create audit log
    action = 'activate' if product.is_active else 'deactivate'
    create_audit_log(product, action, request.user, {
        'is_active': {'old': old_status, 'new': product.is_active}
    })
    
    # Return updated product data
    if product_type == 'package':
        serializer = PackageSerializer(product, context={'request': request})
    else:
        serializer = CampaignSerializer(product, context={'request': request})
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_product_audit_logs(request, product_type, product_id):
    """Get audit logs for a specific product"""
    if product_type == 'package':
        product = get_object_or_404(Package, id=product_id)
        content_type = ContentType.objects.get_for_model(Package)
    elif product_type == 'campaign':
        product = get_object_or_404(Campaign, id=product_id)
        content_type = ContentType.objects.get_for_model(Campaign)
    else:
        return Response(
            {'error': 'Invalid product type. Must be "package" or "campaign"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logs = ProductAuditLog.objects.filter(
        content_type=content_type,
        object_id=product_id
    ).select_related('user').order_by('-timestamp')
    
    serializer = ProductAuditLogSerializer(logs, many=True)
    return Response(serializer.data)



class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product images.
    Supports both public viewing and admin management.
    """
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    lookup_field = 'pk'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    
    def get_permissions(self):
        """Allow public read access, admin-only write access"""
        # Allow OPTIONS requests without authentication
        if self.request.method == 'OPTIONS':
            return [AllowAny()]
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # For admin operations, check if user is staff
        from authentication.permissions import IsAdmin
        return [IsAdmin()]
    
    def get_serializer_class(self):
        """Use write serializer for create/update operations"""
        if self.action in ['create', 'update', 'partial_update']:
            return ProductImageWriteSerializer
        return ProductImageSerializer
    
    def get_queryset(self):
        """Filter images by product type and ID"""
        product_type = self.kwargs.get('product_type')
        product_id = self.kwargs.get('product_id')
        
        if product_type and product_id:
            # Get the content type for the product
            if product_type == 'package':
                content_type = ContentType.objects.get_for_model(Package)
            elif product_type == 'campaign':
                content_type = ContentType.objects.get_for_model(Campaign)
            else:
                return ProductImage.objects.none()
            
            return ProductImage.objects.filter(
                content_type=content_type,
                object_id=product_id
            ).order_by('order', '-uploaded_at')
        
        return ProductImage.objects.all()
    
    def list(self, request, *args, **kwargs):
        """List images for a product (or all images if no product specified)"""
        product_type = kwargs.get('product_type')
        product_id = kwargs.get('product_id')
        
        # If product_type and product_id are provided, filter by product
        if product_type and product_id:
            # Verify product exists
            if product_type == 'package':
                get_object_or_404(Package, id=product_id)
            elif product_type == 'campaign':
                get_object_or_404(Campaign, id=product_id)
            else:
                return Response(
                    {'error': 'Invalid product type. Must be "package" or "campaign"'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get queryset (will be filtered if product_type/product_id are in kwargs)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Upload a new image for a product"""
        product_type = kwargs.get('product_type')
        product_id = kwargs.get('product_id')
        
        if not product_type or not product_id:
            return Response(
                {'error': 'Product type and ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the product
        if product_type == 'package':
            product = get_object_or_404(Package, id=product_id)
            content_type = ContentType.objects.get_for_model(Package)
        elif product_type == 'campaign':
            product = get_object_or_404(Campaign, id=product_id)
            content_type = ContentType.objects.get_for_model(Campaign)
        else:
            return Response(
                {'error': 'Invalid product type. Must be "package" or "campaign"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if product already has 10 images
        existing_count = ProductImage.objects.filter(
            content_type=content_type,
            object_id=product.id
        ).count()
        
        if existing_count >= 10:
            return Response(
                {'error': 'Maximum of 10 images allowed per product'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the image
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # If order is not provided, set it to the next available order
        if 'order' not in request.data or request.data['order'] is None:
            max_order = ProductImage.objects.filter(
                content_type=content_type,
                object_id=product.id
            ).aggregate(models.Max('order'))['order__max']
            order = (max_order or 0) + 1
            image = serializer.save(content_type=content_type, object_id=product.id, order=order)
        else:
            image = serializer.save(content_type=content_type, object_id=product.id)
        
        # If this is the first image, make it primary
        if existing_count == 0:
            image.is_primary = True
            image.save()
        
        # Return full image data
        response_serializer = ProductImageSerializer(image, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update image details (not the image file itself)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Don't allow updating the image file itself
        if 'image' in request.data:
            return Response(
                {'error': 'Cannot update image file. Delete and upload a new one instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return full image data
        response_serializer = ProductImageSerializer(instance, context={'request': request})
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete an image"""
        print(f"=== DESTROY METHOD CALLED! PK: {kwargs.get('pk')} ===")
        instance = self.get_object()
        was_primary = instance.is_primary
        content_type = instance.content_type
        object_id = instance.object_id
        
        instance.delete()
        
        # If deleted image was primary, set another image as primary
        if was_primary:
            next_image = ProductImage.objects.filter(
                content_type=content_type,
                object_id=object_id
            ).order_by('order').first()
            
            if next_image:
                next_image.is_primary = True
                next_image.save()
        
        return Response(
            {'message': 'Image deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['patch'], url_path='reorder')
    def reorder(self, request, *args, **kwargs):
        """Reorder product images"""
        items_order = request.data.get('items', [])
        
        if not items_order:
            return Response(
                {'error': 'Items array is required with format: [{"id": 1, "order": 0}, ...]'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that all items exist
        item_ids = [item.get('id') for item in items_order if item.get('id') is not None]
        items = ProductImage.objects.filter(id__in=item_ids)
        
        if items.count() != len(item_ids):
            return Response(
                {'error': 'One or more images not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update the order for each item
        updated_items = []
        for item_data in items_order:
            item_id = item_data.get('id')
            new_order = item_data.get('order')
            
            if item_id is not None and new_order is not None:
                ProductImage.objects.filter(id=item_id).update(order=new_order)
                updated_items.append(item_id)
        
        # Return updated items
        updated_queryset = ProductImage.objects.filter(id__in=updated_items).order_by('order')
        serializer = ProductImageSerializer(updated_queryset, many=True, context={'request': request})
        return Response({
            'message': f'Successfully reordered {len(updated_items)} images',
            'items': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='set-primary')
    def set_primary(self, request, pk=None, *args, **kwargs):
        """Set an image as the primary image for the product"""
        instance = self.get_object()
        
        # Unset other primary images for the same product
        ProductImage.objects.filter(
            content_type=instance.content_type,
            object_id=instance.object_id,
            is_primary=True
        ).exclude(id=instance.id).update(is_primary=False)
        
        # Set this image as primary
        instance.is_primary = True
        instance.save()
        
        # Return full image data
        serializer = ProductImageSerializer(instance, context={'request': request})
        return Response({
            'message': 'Image set as primary successfully',
            'image': serializer.data
        })


# Function-based view for managing product images (workaround for ViewSet routing issue)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])  # Will check permissions based on method
def manage_product_image(request, pk):
    """Manage a product image by ID"""
    print(f"=== manage_product_image called! Method: {request.method}, PK: {pk} ===")
    # Check permissions based on method
    if request.method != 'GET' and not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        image = ProductImage.objects.get(pk=pk)
    except ProductImage.DoesNotExist:
        return Response(
            {'error': 'Image not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = ProductImageSerializer(image, context={'request': request})
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        # Don't allow updating the image file itself
        if 'image' in request.data:
            return Response(
                {'error': 'Cannot update image file. Delete and upload a new one instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProductImageWriteSerializer(
            image, 
            data=request.data, 
            partial=(request.method == 'PATCH')
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return full image data
        response_serializer = ProductImageSerializer(image, context={'request': request})
        return Response(response_serializer.data)
    
    elif request.method == 'DELETE':
        was_primary = image.is_primary
        content_type = image.content_type
        object_id = image.object_id
        
        image.delete()
        
        # If deleted image was primary, set another image as primary
        if was_primary:
            next_image = ProductImage.objects.filter(
                content_type=content_type,
                object_id=object_id
            ).order_by('order').first()
            
            if next_image:
                next_image.is_primary = True
                next_image.save()
        
        return Response(
            {'message': 'Image deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


# Test endpoint
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([AllowAny])
def test_endpoint(request):
    return Response({'method': request.method, 'message': 'Test endpoint works!'})
