# notifications/routing.py — WebSocket URL routing

from django.urls import re_path
from .consumers import NotificationConsumer

websocket_urlpatterns = [
    # All WebSocket connections go to our consumer
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]