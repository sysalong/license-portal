"""
WSGI config for license_portal project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os
import sys

sys.path.insert(len(sys.path) - 2, '/home/appdep/license_portal_env/lib/python3.7/site-packages')

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(len(sys.path) - 2, path)

from django.core.wsgi import get_wsgi_application

os.environ["DJANGO_SETTINGS_MODULE"] = "license_portal.settings"

application = get_wsgi_application()
