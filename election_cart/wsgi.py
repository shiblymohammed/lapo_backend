"""
WSGI config for election_cart project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'election_cart.settings')

application = get_wsgi_application()
