from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.db.models import Count
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
import logging
from .models import CustomUser
from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer
from .authentication import generate_jwt_token
from .permissions import IsAdmin

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login(request):
    """
    Login with username and password.
    Endpoint: POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    
    Rate Limit: 5 requests per minute per IP address
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate JWT token
        jwt_token = generate_jwt_token(user)
        
        # Serialize user data
        user_data = UserSerializer(user).data
        
        return Response({
            'token': jwt_token,
            'user': user_data,
            'role': user.role
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Authentication failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/h', method='POST', block=True)
def signup(request):
    """
    Create new user account.
    Endpoint: POST /api/auth/signup/
    Body: { "username": "...", "password": "...", "phone_number": "..." }
    
    Rate Limit: 3 requests per hour per IP address
    """
    username = request.data.get('username')
    password = request.data.get('password')
    phone_number = request.data.get('phone_number', '')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            phone_number=phone_number,
            role='user'
        )
        
        # Generate JWT token
        jwt_token = generate_jwt_token(user)
        
        # Serialize user data
        user_data = UserSerializer(user).data
        
        return Response({
            'token': jwt_token,
            'user': user_data,
            'role': user.role,
            'message': 'Account created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Signup failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    Get current user profile.
    Endpoint: GET /api/auth/me/
    """
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)



# ============================================================================
# USER MANAGEMENT ENDPOINTS (Admin only)
# ============================================================================

class UserListView(generics.ListAPIView):
    """
    GET /api/auth/users/
    List all users with their roles and order counts
    Admin only
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None  # Disable pagination
    
    def get_queryset(self):
        queryset = CustomUser.objects.annotate(
            order_count=Count('orders')
        ).order_by('-created_at')
        
        # Filter by role
        role_filter = self.request.query_params.get('role', None)
        if role_filter:
            queryset = queryset.filter(role=role_filter)
        
        # Search by phone or username
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                phone_number__icontains=search
            ) | queryset.filter(
                username__icontains=search
            )
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def create_user(request):
    """
    POST /api/auth/users/create/
    Create a new user (typically staff account)
    Admin only
    """
    serializer = UserCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create user
    user = CustomUser.objects.create_user(
        username=serializer.validated_data['username'],
        phone_number=serializer.validated_data['phone_number'],
        role=serializer.validated_data.get('role', 'user'),
        password=serializer.validated_data.get('password', CustomUser.objects.make_random_password())
    )
    
    # Set firebase_uid if provided
    firebase_uid = serializer.validated_data.get('firebase_uid')
    if firebase_uid:
        user.firebase_uid = firebase_uid
        user.save()
    
    return Response({
        'success': True,
        'message': 'User created successfully',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdmin])
def update_user_role(request, user_id):
    """
    PATCH /api/auth/users/{id}/role/
    Update a user's role
    Admin only
    """
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserUpdateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Update role
    new_role = serializer.validated_data['role']
    user.role = new_role
    user.save()
    
    return Response({
        'success': True,
        'message': f'User role updated to {new_role}',
        'user': UserSerializer(user).data
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmin])
def delete_user(request, user_id):
    """
    DELETE /api/auth/users/{id}/
    Delete a user
    Admin only
    """
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Prevent deleting yourself
    if user.id == request.user.id:
        return Response({
            'success': False,
            'message': 'You cannot delete your own account'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete user
    username = user.username
    user.delete()
    
    return Response({
        'success': True,
        'message': f'User {username} deleted successfully'
    }, status=status.HTTP_200_OK)
