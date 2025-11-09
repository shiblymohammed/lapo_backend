"""Views for serving secure files"""
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.conf import settings
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from products.models import ProductImage
from orders.models import DynamicResourceSubmission, OrderResource
import os
import mimetypes


@api_view(['GET'])
@permission_classes([])  # No DRF permission check - we handle auth manually
def serve_product_image(request, image_id):
    """
    Serve product images securely.
    Public access for product images (authenticated users only).
    Supports authentication via Bearer token in header or 'token' query parameter.
    """
    from authentication.authentication import decode_jwt_token
    from authentication.models import CustomUser
    
    # Try to authenticate user
    user = None
    
    # First try header authentication
    if request.user and request.user.is_authenticated:
        user = request.user
    else:
        # Try token from query parameter
        token = request.GET.get('token')
        if token:
            try:
                payload = decode_jwt_token(token)
                user_id = payload.get('user_id')
                user = CustomUser.objects.get(id=user_id)
            except Exception as e:
                print(f"Token authentication failed: {e}")
                pass
    
    if not user:
        return HttpResponseForbidden("Authentication required")
    
    try:
        image = ProductImage.objects.get(id=image_id)
        
        # Get file field
        if request.GET.get('thumbnail') == 'true' and image.thumbnail:
            file_field = image.thumbnail
        else:
            file_field = image.image
        
        # Use storage backend to open file
        try:
            file_obj = file_field.open('rb')
        except Exception as e:
            raise Http404(f"Image file not found: {str(e)}")
        
        # Determine content type from filename
        filename = file_field.name
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Serve file
        response = FileResponse(file_obj, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(filename)}"'
        
        return response
        
    except ProductImage.DoesNotExist:
        raise Http404("Image not found")
    except Exception as e:
        raise Http404(f"Error serving image: {str(e)}")


@api_view(['GET'])
@permission_classes([])  # No DRF permission check - we handle auth manually
def serve_dynamic_resource(request, submission_id):
    """
    Serve dynamic resource files securely.
    Only accessible by the user who uploaded it or admin staff.
    Supports authentication via Bearer token in header or 'token' query parameter.
    """
    from authentication.authentication import decode_jwt_token
    from authentication.models import CustomUser
    
    # Try to authenticate user
    user = None
    
    # First try header authentication
    if request.user and request.user.is_authenticated:
        user = request.user
    else:
        # Try token from query parameter
        token = request.GET.get('token')
        if token:
            try:
                # Decode custom JWT token
                payload = decode_jwt_token(token)
                user_id = payload.get('user_id')
                user = CustomUser.objects.get(id=user_id)
            except Exception as e:
                print(f"Token authentication failed: {e}")
                pass
    
    if not user:
        return HttpResponseForbidden("Authentication required")
    
    try:
        submission = DynamicResourceSubmission.objects.select_related(
            'order_item__order__user'
        ).get(id=submission_id)
        
        # Check permissions
        if not (user == submission.order_item.order.user or 
                user.is_staff or 
                user == submission.order_item.order.assigned_to):
            return HttpResponseForbidden("You don't have permission to access this file")
        
        # Get file
        if not submission.file_value:
            raise Http404("No file associated with this submission")
        
        # Use storage backend to open file (works with both local and cloud storage)
        try:
            file_obj = submission.file_value.open('rb')
        except Exception as e:
            raise Http404(f"File not found: {str(e)}")
        
        # Determine content type from filename
        filename = submission.file_value.name
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Serve file
        response = FileResponse(file_obj, content_type=content_type)
        
        # For documents, force download; for images, display inline
        if submission.field_definition.field_type == 'document':
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(filename)}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(filename)}"'
        
        return response
        
    except DynamicResourceSubmission.DoesNotExist:
        raise Http404("Resource not found")
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")


@api_view(['GET'])
@permission_classes([])  # No DRF permission check - we handle auth manually
def serve_order_resource(request, order_id, resource_type):
    """
    Serve order resource files (candidate photos, logos, etc.).
    Only accessible by the order owner, assigned staff, or admin.
    Supports authentication via Bearer token in header or 'token' query parameter.
    """
    from authentication.authentication import decode_jwt_token
    from authentication.models import CustomUser
    
    # Try to authenticate user
    user = None
    
    # First try header authentication
    if request.user and request.user.is_authenticated:
        user = request.user
    else:
        # Try token from query parameter
        token = request.GET.get('token')
        if token:
            try:
                payload = decode_jwt_token(token)
                user_id = payload.get('user_id')
                user = CustomUser.objects.get(id=user_id)
            except Exception as e:
                print(f"Token authentication failed: {e}")
                pass
    
    if not user:
        return HttpResponseForbidden("Authentication required")
    
    try:
        from orders.models import Order
        
        order = Order.objects.select_related('user', 'assigned_to').get(id=order_id)
        
        # Check permissions
        if not (user == order.user or 
                user.is_staff or 
                user == order.assigned_to):
            return HttpResponseForbidden("You don't have permission to access this file")
        
        # Get order resource
        order_item = order.items.first()
        if not order_item or not hasattr(order_item, 'resources'):
            raise Http404("Order resources not found")
        
        resources = order_item.resources
        
        # Get the requested file
        if resource_type == 'candidate_photo':
            file_field = resources.candidate_photo
        elif resource_type == 'party_logo':
            file_field = resources.party_logo
        else:
            raise Http404("Invalid resource type")
        
        # Use storage backend to open file
        try:
            file_obj = file_field.open('rb')
        except Exception as e:
            raise Http404(f"File not found: {str(e)}")
        
        # Determine content type from filename
        filename = file_field.name
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Serve file
        response = FileResponse(file_obj, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(filename)}"'
        
        return response
        
    except Order.DoesNotExist:
        raise Http404("Order not found")
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")
