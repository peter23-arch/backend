# restaurants/views.py — CRUD for restaurants

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Restaurant
from .serializers import RestaurantSerializer, RestaurantCreateSerializer


class RestaurantListView(APIView):
    """
    GET — Public: list all active restaurants
    POST — Platform admin: register a new restaurant (no manager yet — assigned separately)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        search = request.query_params.get('search', '')
        if request.user.is_authenticated and request.user.is_platform_admin:
            restaurants = Restaurant.objects.all()
        else:
            restaurants = Restaurant.objects.filter(status='active')
        if search:
            restaurants = restaurants.filter(name__icontains=search)
        serializer = RestaurantSerializer(restaurants, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if not request.user.is_platform_admin:
            return Response({'error': 'Only platform admin can register restaurants.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = RestaurantCreateSerializer(data=request.data)
        if serializer.is_valid():
            restaurant = serializer.save(manager=None)
            return Response(
                RestaurantSerializer(restaurant, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RestaurantDetailView(APIView):
    """
    GET — Public: get single restaurant details
    PUT — Manager or admin: update restaurant
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, pk):
        restaurant = get_object_or_404(Restaurant, pk=pk)
        serializer = RestaurantSerializer(restaurant, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        restaurant = get_object_or_404(Restaurant, pk=pk)
        if not (request.user.is_platform_admin or restaurant.manager == request.user):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RestaurantCreateSerializer(restaurant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(RestaurantSerializer(restaurant, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RestaurantSuspendView(APIView):
    """Admin only — suspend or reactivate a restaurant"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        restaurant = get_object_or_404(Restaurant, pk=pk)
        action = request.data.get('action')

        if action == 'suspend':
            restaurant.status = 'suspended'
        elif action == 'activate':
            restaurant.status = 'active'
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        restaurant.save()
        return Response(RestaurantSerializer(restaurant, context={'request': request}).data)


class AssignManagerView(APIView):
    """Admin only — assign an existing customer as manager of this restaurant"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        restaurant = get_object_or_404(Restaurant, pk=pk)
        if restaurant.manager is not None:
            return Response({'error': 'This restaurant already has a manager.'}, status=status.HTTP_400_BAD_REQUEST)

        from users.models import User
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.role != 'customer':
            return Response({'error': 'Only customer accounts can be promoted to manager.'}, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(user, 'restaurant'):
            return Response({'error': 'This user already manages a restaurant.'}, status=status.HTTP_400_BAD_REQUEST)

        user.role = 'restaurant_manager'
        user.save(update_fields=['role'])
        restaurant.manager = user
        restaurant.save(update_fields=['manager'])

        from users.serializers import UserSerializer
        updated_user_data = UserSerializer(user, context={'request': request}).data

        # Instantly flip that user's interface, even mid-session
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}',
            {
                'type': 'role_changed',
                'message': {
                    'type': 'ROLE_CHANGED',
                    'user': updated_user_data,
                }
            }
        )

        return Response(RestaurantSerializer(restaurant, context={'request': request}).data)


class RemoveManagerView(APIView):
    """Admin only — strip a manager's role and detach them from the restaurant"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        restaurant = get_object_or_404(Restaurant, pk=pk)
        if restaurant.manager is None:
            return Response({'error': 'This restaurant has no manager to remove.'}, status=status.HTTP_400_BAD_REQUEST)

        old_manager = restaurant.manager
        restaurant.manager = None
        restaurant.save(update_fields=['manager'])

        old_manager.role = 'customer'
        old_manager.save(update_fields=['role'])

        from users.serializers import UserSerializer
        updated_user_data = UserSerializer(old_manager, context={'request': request}).data

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{old_manager.id}',
            {
                'type': 'role_changed',
                'message': {
                    'type': 'ROLE_CHANGED',
                    'user': updated_user_data,
                }
            }
        )

        return Response(RestaurantSerializer(restaurant, context={'request': request}).data)


class MyRestaurantView(APIView):
    """Restaurant manager gets their own restaurant details"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_restaurant_manager:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            restaurant = request.user.restaurant
        except Restaurant.DoesNotExist:
            return Response({'error': 'No restaurant found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RestaurantSerializer(restaurant, context={'request': request})
        return Response(serializer.data)


class RestaurantDeleteView(APIView):
    """Admin only — permanently delete a restaurant and everything linked to it"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        restaurant = get_object_or_404(Restaurant, pk=pk)
        name = restaurant.name
        restaurant.delete()

        return Response(
            {'message': f'"{name}" and all its data have been permanently deleted.'},
            status=status.HTTP_200_OK
        )