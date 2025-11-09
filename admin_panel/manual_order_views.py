"""
Manual Order Creation and Management Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

from authentication.models import CustomUser
from authentication.permissions import IsAdmin, IsAdminOrStaff
from orders.models import Order, OrderItem, PaymentRecord, OrderStatusHistory
from products.models import Campaign, Package
from .serializers import (
    CreateManualOrderSerializer,
    AdminOrderDetailSerializer,
    UserBasicSerializer,
    OrderStatusUpdateSerializer,
    RecordPaymentSerializer,
    PaymentRecordSerializer,
    ProductForOrderSerializer
)
from .checklist_service import ChecklistService
from .services import NotificationService
from .cache_utils import invalidate_analytics_cache


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def create_manual_order(request):
    """
    POST /api/admin/orders/manual/
    Create a manual order for offline leads
    
    Body:
    {
      "customer": {
        "name": "John Doe",
        "phone": "+919876543210",
        "email": "john@example.com"
      },
      "items": [
        {
          "product_type": "campaign",
          "product_id": 5,
          "quantity": 1
        }
      ],
      "order_source": "phone_call",
      "payment_status": "paid",
      "payment_method": "cash",
      "payment_amount": 5000,
      "assigned_to": 3,
      "priority": "normal",
      "notes": "Customer wants delivery by Friday"
    }
    """
    serializer = CreateManualOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # 1. Get or create customer
            customer_data = data['customer']
            customer, created = CustomUser.objects.get_or_create(
                phone_number=customer_data['phone'],
                defaults={
                    'first_name': customer_data['name'],
                    'email': customer_data.get('email', ''),
                    'role': 'customer',
                    'is_active': True,
                    'username': customer_data['phone']  # Use phone as username
                }
            )
            
            # Update customer info if exists
            if not created:
                if customer_data['name']:
                    customer.first_name = customer_data['name']
                if customer_data.get('email'):
                    customer.email = customer_data['email']
                customer.save()
            
            # 2. Calculate total amount
            total_amount = Decimal('0.00')
            items_data = []
            
            for item in data['items']:
                if item['product_type'] == 'campaign':
                    product = Campaign.objects.get(id=item['product_id'], is_active=True)
                else:
                    product = Package.objects.get(id=item['product_id'], is_active=True)
                
                item_total = product.price * item['quantity']
                total_amount += item_total
                
                items_data.append({
                    'product': product,
                    'product_type': item['product_type'],
                    'quantity': item['quantity'],
                    'price': product.price
                })
            
            # 3. Create order
            order = Order.objects.create(
                user=customer,
                total_amount=total_amount,
                status='ready_for_processing',  # Manual orders skip resource upload
                is_manual_order=True,
                order_source=data['order_source'],
                created_by=request.user,
                payment_status=data.get('payment_status', 'unpaid'),
                priority=data.get('priority', 'normal'),
                admin_notes=data.get('notes', '')
            )
            
            # Record initial status
            OrderStatusHistory.objects.create(
                order=order,
                old_status='',
                new_status='ready_for_processing',
                changed_by=request.user,
                reason=f'Manual order created via {data["order_source"]}',
                is_manual_change=False
            )
            
            # 4. Create order items
            for item_data in items_data:
                content_type = ContentType.objects.get_for_model(item_data['product'])
                OrderItem.objects.create(
                    order=order,
                    content_type=content_type,
                    object_id=item_data['product'].id,
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    resources_uploaded=True  # Manual orders don't need resource upload
                )
            
            # 5. Handle payment if provided
            if data.get('payment_status') in ['paid', 'partial']:
                payment_amount = data.get('payment_amount', total_amount)
                
                PaymentRecord.objects.create(
                    order=order,
                    amount=payment_amount,
                    payment_method=data.get('payment_method', 'cash'),
                    payment_reference=data.get('payment_reference', ''),
                    recorded_by=request.user,
                    notes=f"Initial payment for manual order"
                )
                
                # Update order if fully paid
                if payment_amount >= total_amount:
                    order.payment_completed_at = timezone.now()
                    order.save()
            
            # 6. Assign to staff if specified
            if data.get('assigned_to'):
                try:
                    staff_user = CustomUser.objects.get(
                        id=data['assigned_to'],
                        role__in=['staff', 'admin']
                    )
                    order.assigned_to = staff_user
                    order.status = 'assigned'
                    order.save()
                    
                    # Record status change
                    OrderStatusHistory.objects.create(
                        order=order,
                        old_status='ready_for_processing',
                        new_status='assigned',
                        changed_by=request.user,
                        reason=f'Assigned to {staff_user.first_name or staff_user.username}',
                        is_manual_change=False
                    )
                    
                    # Notify staff
                    try:
                        NotificationService.notify_staff_order_assigned(order, staff_user)
                    except Exception as e:
                        print(f"Failed to send notification: {e}")
                
                except CustomUser.DoesNotExist:
                    pass  # Continue without assignment if staff not found
            
            # 7. Invalidate cache
            invalidate_analytics_cache()
            
            # Return response
            order_serializer = AdminOrderDetailSerializer(order)
            
            return Response({
                'success': True,
                'message': 'Manual order created successfully',
                'order': order_serializer.data
            }, status=status.HTTP_201_CREATED)
            
    except (Campaign.DoesNotExist, Package.DoesNotExist):
        return Response({
            'success': False,
            'message': 'Product not found or inactive'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def search_customers(request):
    """
    GET /api/admin/customers/search/?q=phone_or_name
    Search for existing customers
    """
    query = request.query_params.get('q', '').strip()
    
    if not query:
        return Response({'customers': []})
    
    # Search by phone or name
    customers = CustomUser.objects.filter(
        Q(phone_number__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query),
        role='customer'
    )[:10]
    
    serializer = UserBasicSerializer(customers, many=True)
    return Response({'customers': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_products_for_order(request):
    """
    GET /api/admin/products/for-order/
    Get all active products for order creation
    """
    campaigns = Campaign.objects.filter(is_active=True)
    packages = Package.objects.filter(is_active=True)
    
    campaigns_data = [{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'price': float(c.price),
        'type': 'campaign',
        'is_active': c.is_active
    } for c in campaigns]
    
    packages_data = [{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': float(p.price),
        'type': 'package',
        'is_active': p.is_active
    } for p in packages]
    
    return Response({
        'campaigns': campaigns_data,
        'packages': packages_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def record_payment(request, order_id):
    """
    POST /api/admin/orders/{id}/record-payment/
    Record a payment for an order
    
    Body:
    {
      "amount": 5000,
      "payment_method": "cash",
      "payment_reference": "CASH-001",
      "notes": "Received at office"
    }
    """
    order = get_object_or_404(Order, id=order_id)
    
    serializer = RecordPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create payment record
    payment = PaymentRecord.objects.create(
        order=order,
        amount=serializer.validated_data['amount'],
        payment_method=serializer.validated_data['payment_method'],
        payment_reference=serializer.validated_data.get('payment_reference', ''),
        payment_proof=serializer.validated_data.get('payment_proof'),
        recorded_by=request.user,
        notes=serializer.validated_data.get('notes', '')
    )
    
    # Update payment status
    order.update_payment_status()
    
    # Update order status if needed
    if order.payment_status == 'paid' and order.status == 'pending_payment':
        order.status = 'pending_resources' if not order.is_manual_order else 'ready_for_processing'
        order.save()
    
    # Get updated totals
    total_paid = order.get_total_paid()
    balance = order.get_payment_balance()
    
    return Response({
        'success': True,
        'message': 'Payment recorded successfully',
        'payment': PaymentRecordSerializer(payment).data,
        'total_paid': float(total_paid),
        'balance': float(balance),
        'fully_paid': total_paid >= order.total_amount
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def update_payment_status(request, order_id):
    """
    POST /api/admin/orders/{id}/update-payment-status/
    Manually update payment status
    
    Body:
    {
      "payment_status": "paid"
    }
    """
    order = get_object_or_404(Order, id=order_id)
    
    payment_status = request.data.get('payment_status')
    
    if not payment_status:
        return Response({
            'success': False,
            'message': 'payment_status is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    valid_statuses = ['unpaid', 'partial', 'paid', 'refunded', 'cod']
    if payment_status not in valid_statuses:
        return Response({
            'success': False,
            'message': f'Invalid payment status. Must be one of: {", ".join(valid_statuses)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    old_payment_status = order.payment_status
    order.payment_status = payment_status
    
    # Set payment_completed_at if marking as paid
    if payment_status == 'paid' and not order.payment_completed_at:
        order.payment_completed_at = timezone.now()
    
    order.save()
    
    # Invalidate cache
    invalidate_analytics_cache()
    
    return Response({
        'success': True,
        'message': f'Payment status updated from {old_payment_status} to {payment_status}',
        'order': AdminOrderDetailSerializer(order).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def update_order_status(request, order_id):
    """
    POST /api/admin/orders/{id}/update-status/
    Manually update order status
    
    Body:
    {
      "status": "in_progress",
      "reason": "Customer sent resources via WhatsApp"
    }
    """
    order = get_object_or_404(Order, id=order_id)
    
    serializer = OrderStatusUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    old_status = order.status
    new_status = serializer.validated_data['status']
    reason = serializer.validated_data.get('reason', '')
    
    # Don't update if status is the same
    if old_status == new_status:
        return Response({
            'success': False,
            'message': 'Order is already in this status'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update order status
    order.status = new_status
    order.save()
    
    # Record status change in history
    OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status=new_status,
        changed_by=request.user,
        reason=reason,
        is_manual_change=True
    )
    
    # Handle side effects based on new status
    if new_status == 'cancelled':
        # Unassign staff
        if order.assigned_to:
            order.assigned_to = None
            order.save()
    
    elif new_status == 'on_hold':
        # Notify staff if assigned
        if order.assigned_to:
            try:
                NotificationService.notify_order_on_hold(order)
            except:
                pass
    
    elif new_status == 'assigned' and order.assigned_to:
        # Generate checklist if doesn't exist
        if not hasattr(order, 'checklist'):
            try:
                ChecklistService.generate_checklist_for_order(order)
            except:
                pass
    
    # Invalidate cache
    invalidate_analytics_cache()
    
    return Response({
        'success': True,
        'message': f'Order status updated to {new_status}',
        'order': AdminOrderDetailSerializer(order).data
    })
