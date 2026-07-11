# restaurants/views.py — CRUD for restaurants

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Restaurant
from .serializers import RestaurantSerializer, RestaurantCreateSerializer


class RestaurantListView(APIView):
    """
    GET — Public: list all active restaurants
    POST — Platform admin: register a new restaurant
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        # Optional search by name
        search = request.query_params.get('search', '')
        if request.user.is_authenticated and request.user.is_platform_admin:
            restaurants = Restaurant.objects.all()
        else:
            # For non-admin users (including unauthenticated), show only active restaurants
            restaurants = Restaurant.objects.filter(status='active')
        if search:
            restaurants = restaurants.filter(name__icontains=search)
        serializer = RestaurantSerializer(restaurants, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        # Only platform admin can register a restaurant
        if not request.user.is_platform_admin:
            return Response({'error': 'Only platform admin can register restaurants.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Get the manager user by ID passed in body
        manager_id = request.data.get('manager_id')
        from users.models import User
        try:
            manager = User.objects.get(id=manager_id, role='restaurant_manager')
        except User.DoesNotExist:
            return Response({'error': 'Manager not found or not a restaurant manager role.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Check if manager already has a restaurant
        if hasattr(manager, 'restaurant'):
            return Response({'error': 'This manager already has a restaurant.'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = RestaurantCreateSerializer(data=request.data)
        if serializer.is_valid():
            restaurant = serializer.save(manager=manager)
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

        # Allow changing manager if manager_id is in the request
        manager_id = request.data.get('manager_id')
        if manager_id:
            from users.models import User
            try:
                new_manager = User.objects.get(id=manager_id, role='restaurant_manager')
                restaurant.manager = new_manager
                restaurant.save()
            except User.DoesNotExist:
                return Response(
                    {'error': 'Manager not found.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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
        action = request.data.get('action')  # 'suspend' or 'activate'

        if action == 'suspend':
            restaurant.status = 'suspended'
        elif action == 'activate':
            restaurant.status = 'active'
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        restaurant.save()
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

        # Django cascade handles orders, menu items, reviews automatically
        # because all related models have on_delete=models.CASCADE
        restaurant.delete()

        return Response(
            {'message': f'"{name}" and all its data have been permanently deleted.'},
            status=status.HTTP_200_OK
        )