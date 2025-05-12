# dashboard/routing.py

from django.urls import re_path
from . import consumers

# WebSocket URL patterns for the dashboard app
websocket_urlpatterns = [
    # We'll define a URL pattern for connecting to the greenhouse data feed
    # This is just a placeholder for now, we'll refine it later
    re_path(r'ws/greenhouses/(?P<greenhouse_id>\w+)/data/$', consumers.GreenhouseConsumer.as_asgi()),
]