# restaurants/views.py — CRUD for restaurants

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Value, Avg
from django.db.models.functions import Coalesce
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from notifications.firebase import send_push_to_multiple
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import Restaurant
from .serializers import RestaurantSerializer, RestaurantCreateSerializer


class RestaurantListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        
        if request.user.is_authenticated and request.user.is_platform_admin:
            restaurants = Restaurant.objects.all()
        else:
            restaurants = Restaurant.objects.filter(status='active')
        
        if search:
            restaurants = restaurants.filter(name__icontains=search)
        
        # Order by name for consistent results
        restaurants = restaurants.order_by('name')
        
        serializer = RestaurantSerializer(restaurants, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admin can register restaurants.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RestaurantCreateSerializer(data=request.data)
        if serializer.is_valid():
            restaurant = serializer.save(manager=None)
            restaurant_data = RestaurantSerializer(restaurant, context={'request': request}).data

            # Broadcast to all connected clients
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'broadcast_all',
                {
                    'type': 'restaurant_broadcast', 
                    'message': {
                        'type': 'NEW_RESTAURANT', 
                        'restaurant': restaurant_data
                    }
                }
            )

            # Send push notifications to customers
            User = get_user_model()
            customer_tokens = list(
                User.objects.filter(
                    role='customer', 
                    fcm_token__isnull=False
                )
                .exclude(fcm_token='')
                .values_list('fcm_token', flat=True)
            )
            
            if customer_tokens:
                send_push_to_multiple(
                    tokens=customer_tokens,
                    title='🎉 New restaurant in town!',
                    body=f'{restaurant.name} just joined MoiEats — check it out',
                    data={'type': 'NEW_RESTAURANT', 'restaurant_id': str(restaurant.id)},
                )

            return Response(restaurant_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RestaurantDetailView(APIView):
    """
    GET — Public
    PUT — Manager or admin: update restaurant, including toggling is_open —
    broadcasts live so customers see Open/Closed change instantly
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
        
        # Check permissions
        if not (request.user.is_platform_admin or restaurant.manager == request.user):
            return Response(
                {'error': 'You do not have permission to update this restaurant.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RestaurantCreateSerializer(restaurant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            restaurant_data = RestaurantSerializer(restaurant, context={'request': request}).data

            # Broadcast update
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'broadcast_all',
                {
                    'type': 'restaurant_broadcast', 
                    'message': {
                        'type': 'RESTAURANT_UPDATED', 
                        'restaurant': restaurant_data
                    }
                }
            )

            return Response(restaurant_data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SetPlatformFeeView(APIView):
    """Admin only — set the commission percentage this restaurant pays per completed order"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admins can set fees.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        restaurant = get_object_or_404(Restaurant, pk=pk)
        fee_value = request.data.get('platform_fee_percent')

        try:
            fee_value = float(fee_value)
        except (TypeError, ValueError):
            return Response(
                {'error': 'A valid numeric fee percentage is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if fee_value < 0 or fee_value > 100:
            return Response(
                {'error': 'Fee percentage must be between 0 and 100.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        restaurant.platform_fee_percent = Decimal(str(fee_value))
        restaurant.save(update_fields=['platform_fee_percent'])

        restaurant_data = RestaurantSerializer(restaurant, context={'request': request}).data

        # Notify the restaurant manager's dashboard
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'restaurant_{restaurant.id}_manager',
            {
                'type': 'restaurant_broadcast', 
                'message': {
                    'type': 'FEE_UPDATED', 
                    'restaurant': restaurant_data
                }
            }
        )

        # Also broadcast to all for transparency
        async_to_sync(channel_layer.group_send)(
            'broadcast_all',
            {
                'type': 'restaurant_broadcast', 
                'message': {
                    'type': 'RESTAURANT_UPDATED', 
                    'restaurant': restaurant_data
                }
            }
        )

        return Response(restaurant_data)


class RestaurantStatsView(APIView):
    """Admin OR that restaurant's own manager — order counts, revenue, and
    platform fee breakdown for today and this month. Only COMPLETED orders
    count toward revenue/fee, since that's when money has actually changed hands."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        restaurant = get_object_or_404(Restaurant, pk=pk)
        
        # Check permissions
        if not (request.user.is_platform_admin or restaurant.manager == request.user):
            return Response(
                {'error': 'You do not have permission to view these stats.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        today = timezone.localtime().date()
        all_orders = restaurant.orders.all()

        # Filter orders by date
        today_orders_qs = all_orders.filter(created_at__date=today)
        month_orders_qs = all_orders.filter(
            created_at__year=today.year, 
            created_at__month=today.month
        )

        # Get completed orders
        completed_today = today_orders_qs.filter(status='completed')
        completed_month = month_orders_qs.filter(status='completed')

        # Calculate fee using the restaurant's fee percentage
        fee_percent = restaurant.platform_fee_percent / Decimal('100')
        
        # Annotate with fee amount
        fee_expr = ExpressionWrapper(
            F('total_amount') * Value(fee_percent),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )

        # Calculate revenue and fees
        revenue_today = completed_today.aggregate(
            total=Coalesce(Sum('total_amount'), Value(Decimal('0.00')))
        )['total']
        
        fee_today = completed_today.aggregate(
            total=Coalesce(Sum(fee_expr), Value(Decimal('0.00')))
        )['total']
        
        net_today = revenue_today - fee_today

        revenue_month = completed_month.aggregate(
            total=Coalesce(Sum('total_amount'), Value(Decimal('0.00')))
        )['total']
        
        fee_month = completed_month.aggregate(
            total=Coalesce(Sum(fee_expr), Value(Decimal('0.00')))
        )['total']
        
        net_month = revenue_month - fee_month

        # ✅ FIX: Get review stats - properly handle mixed types
        reviews = restaurant.reviews.all()
        total_reviews = reviews.count()
        
        # ✅ Calculate average rating using Avg() which handles Decimal properly
        avg_result = reviews.aggregate(
            avg=Coalesce(
                Avg('rating'), 
                Value(Decimal('0.00'), output_field=DecimalField(max_digits=3, decimal_places=2))
            )
        )
        average_rating = avg_result['avg']

        return Response({
            'restaurant': RestaurantSerializer(restaurant, context={'request': request}).data,
            'today_orders': today_orders_qs.count(),
            'month_orders': month_orders_qs.count(),
            'total_orders': all_orders.count(),
            'total_reviews': total_reviews,
            'average_rating': str(average_rating) if average_rating is not None else None,
            'platform_fee_percent': str(restaurant.platform_fee_percent),
            'revenue_today': str(revenue_today),
            'fee_today': str(fee_today),
            'net_today': str(net_today),
            'revenue_month': str(revenue_month),
            'fee_month': str(fee_month),
            'net_month': str(net_month),
        })


class RestaurantSuspendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admins can suspend or activate restaurants.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        restaurant = get_object_or_404(Restaurant, pk=pk)
        action = request.data.get('action')

        if action == 'suspend':
            if restaurant.status == 'suspended':
                return Response(
                    {'error': 'Restaurant is already suspended.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            restaurant.status = 'suspended'
            message = f'{restaurant.name} has been suspended.'
            
        elif action == 'activate':
            if restaurant.status == 'active':
                return Response(
                    {'error': 'Restaurant is already active.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            restaurant.status = 'active'
            message = f'{restaurant.name} has been activated.'
            
        else:
            return Response(
                {'error': 'Invalid action. Use "suspend" or "activate".'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        restaurant.save(update_fields=['status'])

        restaurant_data = RestaurantSerializer(restaurant, context={'request': request}).data
        
        # Broadcast to all clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'broadcast_all',
            {
                'type': 'restaurant_broadcast', 
                'message': {
                    'type': 'RESTAURANT_UPDATED', 
                    'restaurant': restaurant_data
                }
            }
        )

        return Response({
            'message': message,
            'restaurant': restaurant_data
        })


class AssignManagerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admins can assign managers.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        restaurant = get_object_or_404(Restaurant, pk=pk)
        
        if restaurant.manager is not None:
            return Response(
                {'error': 'This restaurant already has a manager. Remove the current manager first.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        from users.models import User
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if user.role not in ['customer', 'restaurant_manager']:
            return Response(
                {'error': 'Only customer accounts can be promoted to manager.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already manages another restaurant
        if hasattr(user, 'restaurant') and user.restaurant is not None:
            return Response(
                {'error': f'This user already manages {user.restaurant.name}.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Promote user to manager
        user.role = 'restaurant_manager'
        user.save(update_fields=['role'])
        restaurant.manager = user
        restaurant.save(update_fields=['manager'])

        from users.serializers import UserSerializer
        updated_user_data = UserSerializer(user, context={'request': request}).data
        restaurant_data = RestaurantSerializer(restaurant, context={'request': request}).data

        # Notify the user
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}',
            {
                'type': 'role_changed', 
                'message': {
                    'type': 'ROLE_CHANGED', 
                    'user': updated_user_data
                }
            }
        )
        
        # Broadcast restaurant update
        async_to_sync(channel_layer.group_send)(
            'broadcast_all',
            {
                'type': 'restaurant_broadcast', 
                'message': {
                    'type': 'RESTAURANT_UPDATED', 
                    'restaurant': restaurant_data
                }
            }
        )

        return Response({
            'message': f'{user.email} is now the manager of {restaurant.name}.',
            'restaurant': restaurant_data
        })


class RemoveManagerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admins can remove managers.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        restaurant = get_object_or_404(Restaurant, pk=pk)
        
        if restaurant.manager is None:
            return Response(
                {'error': 'This restaurant has no manager to remove.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        old_manager = restaurant.manager
        restaurant.manager = None
        restaurant.save(update_fields=['manager'])

        old_manager.role = 'customer'
        old_manager.save(update_fields=['role'])

        from users.serializers import UserSerializer
        updated_user_data = UserSerializer(old_manager, context={'request': request}).data
        restaurant_data = RestaurantSerializer(restaurant, context={'request': request}).data

        # Notify the user
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{old_manager.id}',
            {
                'type': 'role_changed', 
                'message': {
                    'type': 'ROLE_CHANGED', 
                    'user': updated_user_data
                }
            }
        )
        
        # Broadcast restaurant update
        async_to_sync(channel_layer.group_send)(
            'broadcast_all',
            {
                'type': 'restaurant_broadcast', 
                'message': {
                    'type': 'RESTAURANT_UPDATED', 
                    'restaurant': restaurant_data
                }
            }
        )

        return Response({
            'message': f'{old_manager.email} has been removed as manager of {restaurant.name}.',
            'restaurant': restaurant_data
        })


class MyRestaurantView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_restaurant_manager:
            return Response(
                {'error': 'Only restaurant managers can access this endpoint.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            restaurant = request.user.restaurant
        except Restaurant.DoesNotExist:
            return Response(
                {'error': 'No restaurant found for this manager.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RestaurantSerializer(restaurant, context={'request': request})
        return Response(serializer.data)


class RestaurantDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admins can delete restaurants.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        restaurant = get_object_or_404(Restaurant, pk=pk)
        name = restaurant.name
        restaurant_id = restaurant.id
        manager = restaurant.manager

        channel_layer = get_channel_layer()

        # Demote manager if exists
        if manager:
            manager.role = 'customer'
            manager.save(update_fields=['role'])

            from users.serializers import UserSerializer
            updated_user_data = UserSerializer(manager, context={'request': request}).data

            async_to_sync(channel_layer.group_send)(
                f'user_{manager.id}',
                {
                    'type': 'role_changed', 
                    'message': {
                        'type': 'ROLE_CHANGED', 
                        'user': updated_user_data
                    }
                }
            )

        # Delete the restaurant
        restaurant.delete()

        # Broadcast deletion
        async_to_sync(channel_layer.group_send)(
            'broadcast_all',
            {
                'type': 'restaurant_broadcast', 
                'message': {
                    'type': 'RESTAURANT_DELETED', 
                    'restaurant_id': restaurant_id
                }
            }
        )

        return Response(
            {'message': f'"{name}" and all its data have been permanently deleted.'}, 
            status=status.HTTP_200_OK
        )