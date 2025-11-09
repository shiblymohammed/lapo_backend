"""
Django settings for election_cart project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Default to False for security - must explicitly set DEBUG=True in development
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'cloudinary_storage',
    'cloudinary',
    'authentication',
    'products',
    'cart',
    'orders',
    'admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static file serving (must be after SecurityMiddleware)
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'election_cart.middleware.RateLimitMiddleware',  # Rate limiting middleware
]

# Keep APPEND_SLASH = True (default) for consistency

ROOT_URLCONF = 'election_cart.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Add templates directory for custom error pages
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'election_cart.wsgi.application'


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

import dj_database_url

# Priority 1: Use DATABASE_URL if provided (Railway, Heroku, etc.)
# Priority 2: Fall back to individual environment variables
# Priority 3: Use SQLite for local development
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ['DATABASE_URL'],
            conn_max_age=300,  # Connection pooling: 5 minutes (optimized for memory)
            conn_health_checks=True,  # Enable connection health checks (Django 4.1+)
            ssl_require=not DEBUG,  # Require SSL in production
        )
    }
    # Note: MAX_CONNS is not a valid PostgreSQL connection option
    # Connection pooling is handled by conn_max_age parameter above
elif os.getenv('DB_NAME'):
    # Manual configuration using individual environment variables
    # Determine SSL mode based on environment
    # - Production (DEBUG=False + not localhost): require SSL
    # - Development or localhost: prefer SSL (use if available, don't require)
    db_host = os.getenv('DB_HOST', 'localhost')
    is_local = db_host in ['localhost', '127.0.0.1', '::1']
    ssl_mode = 'prefer' if (DEBUG or is_local) else 'require'
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'election_cart'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': db_host,
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 300,  # Connection pooling: 5 minutes (optimized for memory)
            'OPTIONS': {
                'sslmode': ssl_mode,
                'connect_timeout': 10,
                'MAX_CONNS': 5,  # Limit connections per worker for memory optimization
            }
        }
    }
else:
    # SQLite for local development (no PostgreSQL required)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("📦 Using SQLite for local development")

# Custom User Model
AUTH_USER_MODEL = 'authentication.CustomUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Secure media storage (outside web root) - Fallback for local development
SECURE_MEDIA_ROOT = os.getenv('SECURE_MEDIA_ROOT', str(BASE_DIR.parent / 'secure_media'))

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB - files larger than this go to temp file
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB - max request size in memory

# File upload permissions
FILE_UPLOAD_PERMISSIONS = 0o640  # rw-r-----
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750  # rwxr-x---

# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', ''),
}

# Use Cloudinary if credentials are provided, otherwise fall back to local storage
USE_CLOUDINARY = all([
    CLOUDINARY_STORAGE['CLOUD_NAME'],
    CLOUDINARY_STORAGE['API_KEY'],
    CLOUDINARY_STORAGE['API_SECRET']
])

if USE_CLOUDINARY:
    # Cloudinary storage for production
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    
    # Configure Cloudinary
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
        api_key=CLOUDINARY_STORAGE['API_KEY'],
        api_secret=CLOUDINARY_STORAGE['API_SECRET'],
        secure=True
    )
else:
    # Local storage for development
    DEFAULT_FILE_STORAGE = 'products.storage.SecureFileStorage'

# CDN Configuration (Cloudinary acts as CDN when enabled)
CDN_BASE_URL = os.getenv('CDN_BASE_URL', None)

# Static cache version for cache busting
STATIC_CACHE_VERSION = os.getenv('STATIC_CACHE_VERSION', '1.0')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings
# Allow all origins in development or if explicitly enabled
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False') == 'True'

if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:5174'
    ).split(',')

CORS_ALLOW_CREDENTIALS = True

# Explicitly allow all HTTP methods including PUT and DELETE
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Firebase settings
FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', '')

# Razorpay settings
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

# Cache settings
# Using LocMemCache for development, can be upgraded to Redis in production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'election-cart-cache',
        'TIMEOUT': 300,  # 5 minutes default timeout
        'OPTIONS': {
            'MAX_ENTRIES': 300,  # Reduced from 1000 to limit memory usage
            'CULL_FREQUENCY': 3,  # Remove 1/3 of entries when MAX_ENTRIES is reached
        }
    }
}

# To use Redis in production, install django-redis and update to:
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#         'TIMEOUT': 300,
#     }
# }


# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

# Use cache for rate limiting (in-memory for single server, Redis for multiple servers)
RATELIMIT_USE_CACHE = 'default'

# Enable rate limiting
RATELIMIT_ENABLE = True

# View to handle rate limit exceeded (returns 429 instead of 403)
RATELIMIT_VIEW = 'django_ratelimit.views.ratelimited'


# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Optimized logging configuration for production
# All logs stream to stdout for Render to capture
# No file handlers to reduce memory overhead

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {asctime} {module} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'products': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'cart': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'admin_panel': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


# ============================================================================
# PRODUCTION SECURITY SETTINGS
# ============================================================================

# Apply security settings only when DEBUG is False (production/staging)
if not DEBUG:
    # HTTPS Settings
    # Redirect all HTTP requests to HTTPS
    SECURE_SSL_REDIRECT = True
    
    # Mark session cookies as secure (only sent over HTTPS)
    SESSION_COOKIE_SECURE = True
    
    # Mark CSRF cookies as secure (only sent over HTTPS)
    CSRF_COOKIE_SECURE = True
    
    # HTTP Strict Transport Security (HSTS)
    # Tell browsers to only access the site via HTTPS for 1 year
    SECURE_HSTS_SECONDS = 31536000  # 1 year in seconds
    
    # Include all subdomains in HSTS policy
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    
    # Allow site to be preloaded into browsers' HSTS preload list
    SECURE_HSTS_PRELOAD = True
    
    # Prevent MIME type sniffing
    # Stops browsers from trying to guess content types
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # Enable browser's XSS filter
    # Helps prevent cross-site scripting attacks
    SECURE_BROWSER_XSS_FILTER = True
    
    # Prevent site from being embedded in frames/iframes
    # Protects against clickjacking attacks
    X_FRAME_OPTIONS = 'DENY'
    
    # Trust X-Forwarded-Proto header from proxy/load balancer
    # Required when behind Railway, Heroku, or other reverse proxies
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Trust X-Forwarded-Host header from proxy
    USE_X_FORWARDED_HOST = True
    
    # Trust X-Forwarded-Port header from proxy
    USE_X_FORWARDED_PORT = True
    
    print("🔒 Production security settings enabled")
else:
    print("⚠️  Development mode - security settings disabled")


# ============================================================================
# SENTRY ERROR TRACKING
# ============================================================================

# Initialize Sentry for error tracking in production
if not DEBUG and os.getenv('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
        ],
        
        # Set traces_sample_rate to 0.0 to disable performance monitoring
        # This keeps costs low on free tier
        traces_sample_rate=0.0,
        
        # Don't send personally identifiable information
        send_default_pii=False,
        
        # Set environment name
        environment=os.getenv('DJANGO_ENVIRONMENT', 'production'),
        
        # Release tracking (optional)
        release=os.getenv('SENTRY_RELEASE', None),
        
        # Sample rate for error events (0.5 = 50% of errors to reduce memory overhead)
        sample_rate=0.5,
        
        # Limit breadcrumbs to reduce memory usage
        max_breadcrumbs=20,
    )
    
    print("📊 Sentry error tracking enabled")
elif not DEBUG:
    print("⚠️  Sentry DSN not configured - error tracking disabled")
else:
    print("ℹ️  Sentry disabled in development mode")
