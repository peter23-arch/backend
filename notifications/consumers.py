# notifications/consumers.py — WebSocket consumer for real-time updates

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for real-time notifications.
    Each user connects to their personal channel AND to any restaurant channel.
    """

    async def connect(self):
        """Called when a WebSocket connection is opened"""
        # Get JWT token from query string
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
        token = params.get('token', '')

        # Validate token and get user
        self.user = await self.get_user_from_token(token)

        if self.user is None:
            # Reject unauthenticated connection
            await self.close()
            return

        # Subscribe user to their personal notification channel
        self.personal_group = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.personal_group, self.channel_name)

        # If user is a restaurant manager, also join their restaurant's manager channel
        restaurant = await self.get_user_restaurant(self.user)
        if restaurant:
            self.manager_group = f'restaurant_{restaurant.id}_manager'
            await self.channel_layer.group_add(self.manager_group, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Called when the WebSocket closes"""
        if hasattr(self, 'personal_group'):
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
        if hasattr(self, 'manager_group'):
            await self.channel_layer.group_discard(self.manager_group, self.channel_name)

    async def receive(self, text_data):
        """
        Called when client sends data over WebSocket.
        Used for subscribing to restaurant channels (for menu updates).
        """
        data = json.loads(text_data)

        # Client can subscribe to a specific restaurant channel
        if data.get('type') == 'SUBSCRIBE_RESTAURANT':
            restaurant_id = data.get('restaurant_id')
            group_name = f'restaurant_{restaurant_id}'
            await self.channel_layer.group_add(group_name, self.channel_name)
            await self.send(text_data=json.dumps({'type': 'SUBSCRIBED', 'restaurant_id': restaurant_id}))

    # --- Message handlers (called by channel layer group_send) ---

    async def new_order(self, event):
        """Delivers new order notification to restaurant manager"""
        await self.send(text_data=json.dumps(event['message']))

    async def order_update(self, event):
        """Delivers order status update to customer"""
        await self.send(text_data=json.dumps(event['message']))

    async def menu_update(self, event):
        """Delivers new menu item notification to subscribed users"""
        await self.send(text_data=json.dumps(event['message']))

    # --- Helper DB methods ---

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Validate JWT and return the User object"""
        try:
            validated_token = AccessToken(token)
            user_id = validated_token['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def get_user_restaurant(self, user):
        """Get the restaurant owned by this user if they are a manager"""
        try:
            if user.role == 'restaurant_manager':
                return user.restaurant
        except Exception:
            pass
        return None