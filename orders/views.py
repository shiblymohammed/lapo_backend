from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django_ratelimit.decorators import ratelimit
import logging
from .models import Order, OrderItem, OrderResource, DynamicResourceSubmission

logger = logging.getLogger(__name__)
from .serializers import (
    OrderSerializer, 
    PaymentVerificationSerializer, 
    ResourceUploadSerializer,
    OrderResourceSerializer
)
from .razorpay_client import razorpay_client
from cart.models import Cart
from admin_panel.services import NotificationService
from admin_panel.cache_utils import invalidate_analytics_cache


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/h', method='POST', block=True)
def create_order(request):
    """
    Create order from cart and generate Razorpay order.
    Endpoint: POST /api/orders/create/
    
    Rate Limit: 10 requests per hour per user
    """
    try:
        # Get user's cart
        cart = Cart.objects.get(user=request.user)
        
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate total
        total_amount = cart.get_total()
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            status='pending_payment'
        )
        
        # Create order items from cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                content_type=cart_item.content_type,
                object_id=cart_item.object_id,
                quantity=cart_item.quantity,
                price=cart_item.content_object.price if cart_item.content_object else 0
            )
        
        # Create Razorpay order
        razorpay_order = razorpay_client.create_order(
            amount=total_amount,
            receipt=order.order_number
        )
        
        # Update order with Razorpay order ID
        order.razorpay_order_id = razorpay_order['id']
        order.save()
        
        # Clear cart
        cart.items.all().delete()
        
        # Invalidate analytics cache
        invalidate_analytics_cache()
        
        # Return order details with Razorpay order ID
        serializer = OrderSerializer(order)
        return Response({
            'order': serializer.data,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': razorpay_client.client.auth[0],
            'amount': int(total_amount * 100)  # Amount in paise
        }, status=status.HTTP_201_CREATED)
        
    except Cart.DoesNotExist:
        return Response(
            {'error': 'Cart not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Order creation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request, order_id):
    """
    Verify Razorpay payment and update order status.
    Endpoint: POST /api/orders/{id}/payment-success/
    Body: { "razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..." }
    """
    from .models import PaymentHistory
    
    serializer = PaymentVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Verify payment signature
        is_valid = razorpay_client.verify_payment_signature(
            razorpay_order_id=serializer.validated_data['razorpay_order_id'],
            razorpay_payment_id=serializer.validated_data['razorpay_payment_id'],
            razorpay_signature=serializer.validated_data['razorpay_signature']
        )
        
        if not is_valid:
            return Response(
                {'error': 'Payment signature verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use transaction to ensure atomicity
        with transaction.atomic():
            # Update order
            order.razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
            order.razorpay_signature = serializer.validated_data['razorpay_signature']
            order.payment_completed_at = timezone.now()
            order.payment_status = 'paid'
            order.status = 'pending_resources'
            order.save()
            
            # Create payment history record
            payment_history, created = PaymentHistory.objects.get_or_create(
                order=order,
                defaults={
                    'payment_method': 'Razorpay',
                    'transaction_id': serializer.validated_data['razorpay_payment_id'],
                    'amount': order.total_amount,
                    'currency': 'INR',
                    'status': 'completed',
                    'payment_date': order.payment_completed_at,
                    'invoice_number': PaymentHistory.generate_invoice_number(),
                    'metadata': {
                        'razorpay_order_id': serializer.validated_data['razorpay_order_id'],
                        'razorpay_signature': serializer.validated_data['razorpay_signature']
                    }
                }
            )
        
        # Invalidate analytics cache on successful payment
        invalidate_analytics_cache()
        
        # Return updated order
        order_serializer = OrderSerializer(order)
        return Response({
            'success': True,
            'message': 'Payment verified successfully',
            'order': order_serializer.data,
            'invoice_number': payment_history.invoice_number
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Payment verification failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order(request, order_id):
    """
    Get order details.
    Endpoint: GET /api/orders/{id}/
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_orders(request):
    """
    Get all orders for current user.
    Endpoint: GET /api/orders/my-orders/
    """
    orders = Order.objects.filter(user=request.user).select_related(
        'assigned_to'
    ).prefetch_related(
        'items',
        'items__content_type',
        'items__resources',
        'items__dynamic_resources__field_definition'
    ).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@ratelimit(key='user', rate='20/h', method='POST', block=True)
def upload_resources(request, order_id):
    """
    Upload resources for order items.
    Endpoint: POST /api/orders/{id}/upload-resources/
    Content-Type: multipart/form-data
    Body: {
        "order_item_id": int,
        "candidate_photo": file,
        "party_logo": file,
        "campaign_slogan": string,
        "preferred_date": date (YYYY-MM-DD),
        "whatsapp_number": string,
        "additional_notes": string (optional)
    }
    
    Rate Limit: 20 requests per hour per user
    """
    try:
        # Get order and verify ownership
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if order is in correct status
        if order.status not in ['pending_resources', 'ready_for_processing']:
            return Response(
                {'error': f'Cannot upload resources for order with status: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate request data
        serializer = ResourceUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get order item and verify it belongs to this order
        order_item_id = serializer.validated_data['order_item_id']
        try:
            order_item = OrderItem.objects.get(id=order_item_id, order=order)
        except OrderItem.DoesNotExist:
            return Response(
                {'error': 'Order item not found or does not belong to this order'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if resources already exist for this item
        if hasattr(order_item, 'resources'):
            return Response(
                {'error': 'Resources already uploaded for this order item'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create OrderResource with transaction
        with transaction.atomic():
            order_resource = OrderResource.objects.create(
                order_item=order_item,
                candidate_photo=serializer.validated_data['candidate_photo'],
                party_logo=serializer.validated_data['party_logo'],
                campaign_slogan=serializer.validated_data['campaign_slogan'],
                preferred_date=serializer.validated_data['preferred_date'],
                whatsapp_number=serializer.validated_data['whatsapp_number'],
                additional_notes=serializer.validated_data.get('additional_notes', '')
            )
            
            # Mark order item as resources uploaded
            order_item.resources_uploaded = True
            order_item.save()
            
            # Check if all items have resources uploaded
            all_uploaded = order.all_resources_uploaded()
            if all_uploaded:
                order.status = 'ready_for_processing'
                order.save()
                
                # Notify admins that order is ready for processing
                NotificationService.notify_admins_new_order(order)
        
        # Get pending items (items without resources)
        pending_items = []
        for item in order.items.all():
            if not item.resources_uploaded:
                pending_items.append({
                    'id': item.id,
                    'item_type': item.content_type.model,
                    'item_name': str(item.content_object) if item.content_object else 'Unknown',
                    'quantity': item.quantity
                })
        
        # Return response
        resource_serializer = OrderResourceSerializer(order_resource)
        return Response({
            'success': True,
            'message': 'Resources uploaded successfully',
            'resource': resource_serializer.data,
            'order_status': order.status,
            'all_resources_uploaded': all_uploaded,
            'pending_items': pending_items
        }, status=status.HTTP_201_CREATED)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Resource upload failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_resources(request, order_id):
    """
    Get all resources for an order.
    Endpoint: GET /api/orders/{id}/resources/
    """
    try:
        order = Order.objects.prefetch_related(
            'items',
            'items__resources'
        ).get(id=order_id, user=request.user)
        
        # Get all order items with their resources
        items_with_resources = []
        for item in order.items.all():
            item_data = {
                'id': item.id,
                'item_type': item.content_type.model,
                'item_name': str(item.content_object) if item.content_object else 'Unknown',
                'quantity': item.quantity,
                'resources_uploaded': item.resources_uploaded,
                'resources': None
            }
            
            if hasattr(item, 'resources'):
                resource_serializer = OrderResourceSerializer(item.resources)
                item_data['resources'] = resource_serializer.data
            
            items_with_resources.append(item_data)
        
        return Response({
            'order_id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'items': items_with_resources
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_resource_upload_status(request, order_id):
    """
    Get resource upload status and pending items for an order.
    Endpoint: GET /api/orders/{id}/resource-status/
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Get pending items
        pending_items = []
        for item in order.get_pending_resource_items():
            pending_items.append({
                'id': item.id,
                'item_type': item.content_type.model,
                'item_name': str(item.content_object) if item.content_object else 'Unknown',
                'quantity': item.quantity,
                'price': float(item.price)
            })
        
        # Get uploaded items
        uploaded_items = []
        for item in order.items.filter(resources_uploaded=True):
            uploaded_items.append({
                'id': item.id,
                'item_type': item.content_type.model,
                'item_name': str(item.content_object) if item.content_object else 'Unknown',
                'quantity': item.quantity,
                'uploaded_at': item.resources.uploaded_at if hasattr(item, 'resources') else None
            })
        
        return Response({
            'order_id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'total_items': order.get_total_items(),
            'progress_percentage': order.get_resource_upload_progress(),
            'all_resources_uploaded': order.all_resources_uploaded(),
            'pending_items': pending_items,
            'uploaded_items': uploaded_items
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_resource_fields(request, order_id):
    """
    Get required dynamic resource fields for an order.
    Endpoint: GET /api/orders/{id}/resource-fields/
    """
    from products.models import ResourceFieldDefinition
    from django.contrib.contenttypes.models import ContentType
    
    try:
        order = Order.objects.prefetch_related(
            'items',
            'items__dynamic_resources__field_definition'
        ).get(id=order_id, user=request.user)
        
        # Get all order items and their required fields
        items_with_fields = []
        
        for item in order.items.all():
            # Get the content type for this item
            content_type = item.content_type
            product_id = item.object_id
            
            # Get resource field definitions for this product
            fields = ResourceFieldDefinition.objects.filter(
                content_type=content_type,
                object_id=product_id
            ).order_by('order')
            
            # Get existing submissions for this order item
            existing_submissions = DynamicResourceSubmission.objects.filter(
                order_item=item
            ).select_related('field_definition')
            
            # Create a map of field_id to submission
            submission_map = {sub.field_definition.id: sub for sub in existing_submissions}
            
            # Build field list with submission status
            field_list = []
            for field in fields:
                submission = submission_map.get(field.id)
                field_data = {
                    'id': field.id,
                    'field_name': field.field_name,
                    'field_type': field.field_type,
                    'is_required': field.is_required,
                    'order': field.order,
                    'help_text': field.help_text,
                    'max_file_size_mb': field.max_file_size_mb,
                    'max_length': field.max_length,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'allowed_extensions': field.allowed_extensions,
                    'submitted': submission is not None,
                    'submission_id': submission.id if submission else None,
                    'value': None
                }
                
                # Add current value if submitted
                if submission:
                    if field.field_type in ['text', 'phone', 'date']:
                        field_data['value'] = submission.text_value
                    elif field.field_type == 'number':
                        field_data['value'] = submission.number_value
                    elif field.field_type in ['image', 'document']:
                        field_data['value'] = submission.file_value.url if submission.file_value else None
                
                field_list.append(field_data)
            
            items_with_fields.append({
                'order_item_id': item.id,
                'item_type': item.content_type.model,
                'item_name': str(item.content_object) if item.content_object else 'Unknown',
                'quantity': item.quantity,
                'resources_uploaded': item.resources_uploaded,
                'fields': field_list
            })
        
        return Response({
            'order_id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'items': items_with_fields
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def submit_dynamic_resources(request, order_id):
    """
    Submit dynamic resources for an order item.
    Endpoint: POST /api/orders/{id}/submit-resources/
    Content-Type: multipart/form-data
    Body: {
        "order_item_id": int,
        "field_{field_id}": value (text, number, or file)
    }
    """
    from products.models import ResourceFieldDefinition
    from django.core.files.uploadedfile import UploadedFile
    import os
    
    try:
        # Get order and verify ownership
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if order is in correct status
        if order.status not in ['pending_resources', 'ready_for_processing']:
            return Response(
                {'error': f'Cannot upload resources for order with status: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get order item ID
        order_item_id = request.data.get('order_item_id')
        if not order_item_id:
            return Response(
                {'error': 'order_item_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get order item and verify it belongs to this order
        try:
            order_item = OrderItem.objects.get(id=order_item_id, order=order)
        except OrderItem.DoesNotExist:
            return Response(
                {'error': 'Order item not found or does not belong to this order'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get required fields for this product
        content_type = order_item.content_type
        product_id = order_item.object_id
        
        required_fields = ResourceFieldDefinition.objects.filter(
            content_type=content_type,
            object_id=product_id
        )
        
        # Validate and create submissions
        errors = {}
        submissions_created = []
        
        with transaction.atomic():
            for field_def in required_fields:
                field_key = f'field_{field_def.id}'
                field_value = request.data.get(field_key)
                
                # Check if field is required
                if field_def.is_required and not field_value:
                    errors[field_key] = f'{field_def.field_name} is required'
                    continue
                
                # Skip if no value provided for optional field
                if not field_value:
                    continue
                
                # Validate based on field type
                if field_def.field_type in ['text', 'phone', 'date']:
                    # Validate text length
                    if field_def.max_length and len(field_value) > field_def.max_length:
                        errors[field_key] = f'{field_def.field_name} exceeds maximum length of {field_def.max_length}'
                        continue
                    
                    # Create or update submission
                    submission, created = DynamicResourceSubmission.objects.update_or_create(
                        order_item=order_item,
                        field_definition=field_def,
                        defaults={'text_value': field_value}
                    )
                    submissions_created.append(submission)
                
                elif field_def.field_type == 'number':
                    # Validate number
                    try:
                        number_value = int(field_value)
                        
                        if field_def.min_value is not None and number_value < field_def.min_value:
                            errors[field_key] = f'{field_def.field_name} must be at least {field_def.min_value}'
                            continue
                        
                        if field_def.max_value is not None and number_value > field_def.max_value:
                            errors[field_key] = f'{field_def.field_name} must be at most {field_def.max_value}'
                            continue
                        
                        # Create or update submission
                        submission, created = DynamicResourceSubmission.objects.update_or_create(
                            order_item=order_item,
                            field_definition=field_def,
                            defaults={'number_value': number_value}
                        )
                        submissions_created.append(submission)
                    
                    except (ValueError, TypeError):
                        errors[field_key] = f'{field_def.field_name} must be a valid number'
                        continue
                
                elif field_def.field_type in ['image', 'document']:
                    # Validate file
                    if not isinstance(field_value, UploadedFile):
                        errors[field_key] = f'{field_def.field_name} must be a file'
                        continue
                    
                    # Validate file size
                    max_size_bytes = (field_def.max_file_size_mb or 10) * 1024 * 1024
                    if field_value.size > max_size_bytes:
                        errors[field_key] = f'{field_def.field_name} exceeds maximum size of {field_def.max_file_size_mb}MB'
                        continue
                    
                    # Validate file extension
                    if field_def.field_type == 'image':
                        allowed_exts = ['.jpg', '.jpeg', '.png', '.gif']
                    else:
                        allowed_exts = field_def.allowed_extensions or ['.pdf', '.docx', '.doc']
                    
                    file_ext = os.path.splitext(field_value.name)[1].lower()
                    if file_ext not in allowed_exts:
                        errors[field_key] = f'{field_def.field_name} must be one of: {", ".join(allowed_exts)}'
                        continue
                    
                    # Validate file using validators
                    try:
                        from .validators import validate_dynamic_resource_submission
                        validate_dynamic_resource_submission(field_value, field_def)
                    except ValidationError as e:
                        errors[field_key] = str(e)
                        continue
                    
                    # Create or update submission
                    submission, created = DynamicResourceSubmission.objects.update_or_create(
                        order_item=order_item,
                        field_definition=field_def,
                        defaults={'file_value': field_value}
                    )
                    submissions_created.append(submission)
            
            # If there are validation errors, rollback and return errors
            if errors:
                transaction.set_rollback(True)
                return Response({
                    'success': False,
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark order item as resources uploaded
            order_item.resources_uploaded = True
            order_item.save()
            
            # Check if all items have resources uploaded
            all_uploaded = order.all_resources_uploaded()
            if all_uploaded:
                order.status = 'ready_for_processing'
                order.save()
                
                # Notify admins that order is ready for processing
                NotificationService.notify_admins_new_order(order)
        
        # Get pending items
        pending_items = []
        for item in order.items.all():
            if not item.resources_uploaded:
                pending_items.append({
                    'id': item.id,
                    'item_type': item.content_type.model,
                    'item_name': str(item.content_object) if item.content_object else 'Unknown',
                    'quantity': item.quantity
                })
        
        return Response({
            'success': True,
            'message': 'Resources submitted successfully',
            'submissions_count': len(submissions_created),
            'order_status': order.status,
            'all_resources_uploaded': all_uploaded,
            'pending_items': pending_items
        }, status=status.HTTP_201_CREATED)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Resource submission failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request, order_id):
    """
    Get payment history for an order.
    Endpoint: GET /api/orders/{id}/payment-history/
    """
    from .models import PaymentHistory
    from .serializers import PaymentHistorySerializer
    
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if payment history exists
        if not hasattr(order, 'payment_history'):
            return Response(
                {'error': 'Payment history not found for this order'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        payment_history = order.payment_history
        serializer = PaymentHistorySerializer(payment_history)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice(request, order_id):
    """
    Download invoice PDF for an order.
    Endpoint: GET /api/orders/{id}/invoice/download/
    """
    from django.http import HttpResponse
    from .invoice_generator import InvoiceGenerator
    
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if order has been paid
        if not order.payment_completed_at:
            return Response(
                {'error': 'Invoice not available. Payment not completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate invoice
        generator = InvoiceGenerator()
        pdf_buffer = generator.generate_invoice(order)
        filename = generator.get_invoice_filename(order)
        
        # Update invoice_generated_at if payment history exists
        if hasattr(order, 'payment_history'):
            payment_history = order.payment_history
            if not payment_history.invoice_generated_at:
                payment_history.invoice_generated_at = timezone.now()
                payment_history.save()
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Invoice generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_payments(request):
    """
    Get all payment history for current user with optional date range filtering.
    Endpoint: GET /api/orders/my-payments/
    Query params: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), status
    """
    from .models import PaymentHistory
    from .serializers import PaymentHistorySerializer
    from datetime import datetime
    
    try:
        # Get all orders for the user that have payment history
        payment_histories = PaymentHistory.objects.filter(
            order__user=request.user
        ).select_related('order')
        
        # Apply date range filter if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                payment_histories = payment_histories.filter(payment_date__gte=start_date_obj)
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                # Add one day to include the end date
                from datetime import timedelta
                end_date_obj = end_date_obj + timedelta(days=1)
                payment_histories = payment_histories.filter(payment_date__lt=end_date_obj)
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Apply status filter if provided
        payment_status = request.query_params.get('status')
        if payment_status:
            payment_histories = payment_histories.filter(status=payment_status)
        
        # Order by payment date descending
        payment_histories = payment_histories.order_by('-payment_date')
        
        serializer = PaymentHistorySerializer(payment_histories, many=True)
        
        return Response({
            'count': payment_histories.count(),
            'payments': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve payment history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice(request, order_id):
    """
    Download invoice PDF for an order
    Endpoint: GET /api/orders/<order_id>/invoice/
    
    Accessible by:
    - Order owner (customer)
    - Admin users
    - Staff assigned to the order
    """
    from django.http import HttpResponse
    from .invoice_generator import InvoiceGenerator
    
    try:
        # Get the order
        order = Order.objects.select_related(
            'user', 'payment_history', 'assigned_to'
        ).prefetch_related('items', 'items__content_type').get(id=order_id)
        
        # Check permissions
        user = request.user
        is_owner = order.user == user
        is_admin = user.role == 'admin'
        is_assigned_staff = hasattr(order, 'assigned_to') and order.assigned_to == user
        
        if not (is_owner or is_admin or is_assigned_staff):
            return Response(
                {'error': 'You do not have permission to download this invoice'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if order has been paid
        # Allow invoice for orders that are past payment stage OR have successful payment_history
        has_payment_history = hasattr(order, 'payment_history') and order.payment_history.status == 'success'
        is_past_payment = order.status not in ['pending_payment', 'pending_resources']
        
        if not (has_payment_history or is_past_payment):
            return Response(
                {'error': 'Invoice is only available for paid orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate invoice
        try:
            invoice_generator = InvoiceGenerator()
            pdf_buffer = invoice_generator.generate_invoice(order)
            filename = invoice_generator.get_invoice_filename(order)
        except Exception as gen_error:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Invoice generation error: {str(gen_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to generate invoice: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
