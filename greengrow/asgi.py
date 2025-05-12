# greengrow/asgi.py
"""
ASGI config for greengrow project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter
from django.urls import path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import dashboard.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greengrow.settings')


# Get Django's ASGI application
# This handles regular HTTP requests
django_asgi_app = get_asgi_application()

# Define the Protocol Type Router
# It routes incoming connections based on their protocol (HTTP or WebSocket)
application = ProtocolTypeRouter({
    "http": django_asgi_app, # Route HTTP requests to Django's core ASGI app

    "websocket": AuthMiddlewareStack( # Route WebSocket connections
        URLRouter(
            dashboard.routing.websocket_urlpatterns # Route WebSocket URLs to your app's routing
        )
    ),
})