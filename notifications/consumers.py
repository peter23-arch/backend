# notifications/consumers.py — WebSocket consumer for real-time updates

import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for real-time notifications.
    Each user connects to their personal channel, any restaurant channel,
    a shared broadcast channel, and — for platform admins — an admin-only channel.
    """

    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [''])[0]

        self.user = await self.get_user_from_token(token)

        if self.user is None:
            await self.close()
            return

        self.personal_group = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.personal_group, self.channel_name)

        self.broadcast_group = 'broadcast_all'
        await self.channel_layer.group_add(self.broadcast_group, self.channel_name)

        if self.user.is_platform_admin:
            self.admin_group = 'admin_broadcasts'
            await self.channel_layer.group_add(self.admin_group, self.channel_name)

        restaurant = await self.get_user_restaurant(self.user)
        if restaurant:
            self.manager_group = f'restaurant_{restaurant.id}_manager'
            await self.channel_layer.group_add(self.manager_group, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'personal_group'):
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
        if hasattr(self, 'broadcast_group'):
            await self.channel_layer.group_discard(self.broadcast_group, self.channel_name)
        if hasattr(self, 'admin_group'):
            await self.channel_layer.group_discard(self.admin_group, self.channel_name)
        if hasattr(self, 'manager_group'):
            await self.channel_layer.group_discard(self.manager_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'SUBSCRIBE_RESTAURANT':
            restaurant_id = data.get('restaurant_id')
            group_name = f'restaurant_{restaurant_id}'
            await self.channel_layer.group_add(group_name, self.channel_name)
            await self.send(text_data=json.dumps({'type': 'SUBSCRIBED', 'restaurant_id': restaurant_id}))

    async def new_order(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def order_update(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def menu_update(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def new_review(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def review_deleted(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def role_changed(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def restaurant_broadcast(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            validated_token = AccessToken(token)
            user_id = validated_token['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def get_user_restaurant(self, user):
        try:
            if user.role == 'restaurant_manager':
                return user.restaurant
        except Exception:
            pass
        return None