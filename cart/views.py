from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from .models import Cart, CartItem
from .serializers import CartSerializer, AddToCartSerializer
from products.models import Package, Campaign


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart(request):
    """
    Get current user's cart.
    Endpoint: GET /api/cart/
    """
    cart, created = Cart.objects.get_or_create(user=request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """
    Add item to cart.
    Endpoint: POST /api/cart/add/
    Body: { "item_type": "package|campaign", "item_id": 1, "quantity": 1 }
    """
    serializer = AddToCartSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    item_type = serializer.validated_data['item_type']
    item_id = serializer.validated_data['item_id']
    quantity = serializer.validated_data['quantity']
    
    # Get or create cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get the item
    try:
        if item_type == 'package':
            item = Package.objects.get(id=item_id, is_active=True)
            content_type = ContentType.objects.get_for_model(Package)
        elif item_type == 'campaign':
            item = Campaign.objects.get(id=item_id, is_active=True)
            content_type = ContentType.objects.get_for_model(Campaign)
        else:
            return Response(
                {'error': 'Invalid item type'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (Package.DoesNotExist, Campaign.DoesNotExist):
        return Response(
            {'error': f'{item_type.capitalize()} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        content_type=content_type,
        object_id=item_id,
        defaults={'quantity': quantity}
    )
    
    if not created:
        # Item already exists, update quantity
        cart_item.quantity += quantity
        cart_item.save()
    
    # Return updated cart
    cart_serializer = CartSerializer(cart)
    return Response(cart_serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    """
    Remove item from cart.
    Endpoint: DELETE /api/cart/remove/{item_id}/
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        cart_item.delete()
        
        # Return updated cart
        cart_serializer = CartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_200_OK)
    except Cart.DoesNotExist:
        return Response(
            {'error': 'Cart not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except CartItem.DoesNotExist:
        return Response(
            {'error': 'Cart item not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    """
    Clear all items from cart.
    Endpoint: DELETE /api/cart/clear/
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        
        # Return empty cart
        cart_serializer = CartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_200_OK)
    except Cart.DoesNotExist:
        return Response(
            {'error': 'Cart not found'},
            status=status.HTTP_404_NOT_FOUND
        )
