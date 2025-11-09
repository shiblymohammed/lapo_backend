from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
import firebase_admin
from firebase_admin import auth, credentials
import jwt
from datetime import datetime, timedelta
from .models import CustomUser
import os


# Initialize Firebase Admin SDK (optional)
FIREBASE_ENABLED = False
if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
        print("✅ Firebase authentication enabled")
    except Exception as e:
        print(f"⚠️  Firebase initialization error: {e}")
        print("ℹ️  Firebase authentication disabled")
else:
    print("ℹ️  Firebase credentials not provided - Firebase authentication disabled")


def generate_jwt_token(user):
    """
    Generate JWT token for session management after Firebase verification.
    """
    payload = {
        'user_id': user.id,
        'phone_number': user.phone_number,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token


def decode_jwt_token(token):
    """
    Decode and verify JWT token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed('Invalid token')


class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for Firebase token verification.
    Only works if Firebase is enabled.
    """
    
    def authenticate(self, request):
        if not FIREBASE_ENABLED:
            return None
        
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            decoded_token = auth.verify_id_token(token)
            firebase_uid = decoded_token['uid']
            
            try:
                user = CustomUser.objects.get(firebase_uid=firebase_uid)
                return (user, None)
            except CustomUser.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')
                
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
    
    def authenticate_header(self, request):
        return 'Bearer'


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for JWT token verification.
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            payload = decode_jwt_token(token)
            user_id = payload.get('user_id')
            
            try:
                user = CustomUser.objects.get(id=user_id)
                return (user, None)
            except CustomUser.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')
                
        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
    
    def authenticate_header(self, request):
        return 'Bearer'
