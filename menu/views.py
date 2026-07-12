# menu/views.py — Menu item CRUD

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from notifications.firebase import send_push_to_multiple
from django.contrib.auth import get_user_model

from .models import MenuItem, MenuCategory
from .serializers import MenuItemSerializer, MenuItemCreateSerializer, MenuCategorySerializer
from restaurants.models import Restaurant


class MenuListView(APIView):
    """
    GET — Public: get all menu items for a restaurant
    POST — Manager: add a new menu item
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, restaurant_id):
        search = request.query_params.get('search', '')
        items = MenuItem.objects.filter(restaurant_id=restaurant_id)
        if search:
            items = items.filter(name__icontains=search)
        serializer = MenuItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

        if restaurant.manager != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MenuItemCreateSerializer(data=request.data)
        if serializer.is_valid():
            item = serializer.save(restaurant=restaurant)
            item_data = MenuItemSerializer(item, context={'request': request}).data

            # Broadcast instantly to anyone currently viewing this restaurant's page
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{restaurant_id}',
                {
                    'type': 'menu_update',
                    'message': {
                        'type': 'NEW_MENU_ITEM',
                        'restaurant_name': restaurant.name,
                        'item': item_data,
                    }
                }
            )

            # Also push-notify customers who aren't currently on the site
            User = get_user_model()
            customer_tokens = list(
                User.objects.filter(
                    role='customer',
                    fcm_token__isnull=False
                ).exclude(fcm_token='').values_list('fcm_token', flat=True)
            )
            if customer_tokens:
                send_push_to_multiple(
                    tokens=customer_tokens,
                    title=f'✨ New on the menu — {restaurant.name}',
                    body=f'{item.name} is now available!',
                    data={'type': 'NEW_MENU_ITEM', 'restaurant_id': str(restaurant_id)},
                )

            return Response(item_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MenuItemDetailView(APIView):
    """PUT / DELETE a single menu item"""
    permission_classes = [IsAuthenticated]

    def put(self, request, restaurant_id, item_id):
        item = get_object_or_404(MenuItem, pk=item_id, restaurant_id=restaurant_id)

        if item.restaurant.manager != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MenuItemCreateSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(MenuItemSerializer(item, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, restaurant_id, item_id):
        item = get_object_or_404(MenuItem, pk=item_id, restaurant_id=restaurant_id)

        if item.restaurant.manager != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        item.delete()
        return Response({'message': 'Item deleted'}, status=status.HTTP_204_NO_CONTENT)


class MenuAvailabilityView(APIView):
    """Toggle availability of a menu item"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, restaurant_id, item_id):
        item = get_object_or_404(MenuItem, pk=item_id, restaurant_id=restaurant_id)

        if item.restaurant.manager != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        availability = request.data.get('availability')
        if availability not in ['available', 'later', 'unavailable']:
            return Response({'error': 'Invalid availability value'}, status=status.HTTP_400_BAD_REQUEST)

        item.availability = availability
        item.save()
        return Response(MenuItemSerializer(item, context={'request': request}).data)


class MenuCategoryListView(APIView):
    """List and create categories for a restaurant"""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, restaurant_id):
        categories = MenuCategory.objects.filter(restaurant_id=restaurant_id)
        serializer = MenuCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
        if restaurant.manager != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MenuCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(restaurant=restaurant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)