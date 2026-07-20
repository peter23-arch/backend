# orders/views.py — Order placement and management

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from notifications.firebase import send_push_notification, send_push_to_multiple
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.pagination import PageNumberPagination
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer


class OrdersPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PlaceOrderView(APIView):
    """Customer places a new order — blocked if restaurant is closed,
    notifies restaurant manager AND admins in real time"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.data.get('delivery_phone', '').strip():
            return Response({'error': 'A phone number is required to place an order.'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get('delivery_location', '').strip():
            return Response({'error': 'A delivery location is required to place an order.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderCreateSerializer(data=request.data)

        if serializer.is_valid():
            restaurant = serializer.validated_data['restaurant']

            if restaurant.manager is None:
                return Response({'error': 'This restaurant is not yet accepting orders.'}, status=status.HTTP_400_BAD_REQUEST)

            if not restaurant.is_open:
                return Response({'error': f'{restaurant.name} is currently closed and not accepting orders.'}, status=status.HTTP_400_BAD_REQUEST)

            order = serializer.save(customer=request.user)

            # Snapshot the restaurant's current fee onto this order permanently
            order.platform_fee_percent = restaurant.platform_fee_percent
            order.save(update_fields=['platform_fee_percent'])

            order_data = OrderSerializer(order, context={'request': request}).data

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{order.restaurant.id}_manager',
                {'type': 'new_order', 'message': {'type': 'NEW_ORDER', 'order': order_data}}
            )
            async_to_sync(channel_layer.group_send)(
                'admin_broadcasts',
                {'type': 'new_order', 'message': {'type': 'NEW_ORDER', 'order': order_data}}
            )

            manager = order.restaurant.manager
            if manager and manager.fcm_token:
                send_push_notification(
                    token=manager.fcm_token,
                    title=f'🛎️ New Order — {order.restaurant.name}',
                    body=f'Order #{order.id} from {request.user.get_full_name() or request.user.username}',
                    data={'type': 'NEW_ORDER', 'order_id': str(order.id)},
                )

            User = get_user_model()
            admin_tokens = list(
                User.objects.filter(role='platform_admin', fcm_token__isnull=False)
                .exclude(fcm_token='').values_list('fcm_token', flat=True)
            )
            if admin_tokens:
                send_push_to_multiple(
                    tokens=admin_tokens,
                    title=f'🛎️ New Order — {order.restaurant.name}',
                    body=f'Order #{order.id} · KSh {order.total_amount}',
                    data={'type': 'NEW_ORDER', 'order_id': str(order.id)},
                )

            return Response(order_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
        paginator = OrdersPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.customer != request.user and order.restaurant.manager != request.user and not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)


class UpdateOrderStatusView(APIView):
    """Restaurant manager updates order status — notifies customer live,
    and when marked completed, triggers a live stats refresh for manager + admin"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        if order.restaurant.manager != request.user and not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']

        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save()

        order_data = OrderSerializer(order, context={'request': request}).data

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{order.customer.id}',
            {'type': 'order_update', 'message': {'type': 'ORDER_STATUS_UPDATE', 'order': order_data}}
        )

        customer = order.customer
        if customer.fcm_token:
            send_push_notification(
                token=customer.fcm_token,
                title=f'📦 Order Update — {order.restaurant.name}',
                body=f'Your order #{order.id} is now: {order.get_status_display()}',
                data={'type': 'ORDER_UPDATE', 'order_id': str(order.id)},
            )

        # Order successfully completed — tell manager + admin dashboards to refresh their stats
        if new_status == 'completed':
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{order.restaurant.id}_manager',
                {'type': 'order_completed', 'message': {'type': 'ORDER_COMPLETED', 'restaurant_id': order.restaurant.id}}
            )
            async_to_sync(channel_layer.group_send)(
                'admin_broadcasts',
                {'type': 'order_completed', 'message': {'type': 'ORDER_COMPLETED', 'restaurant_id': order.restaurant.id}}
            )

        return Response(order_data)


class RestaurantOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, restaurant_id):
        from restaurants.models import Restaurant
        restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

        if restaurant.manager != request.user and not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')

        range_filter = request.query_params.get('range')
        today = timezone.localtime().date()
        if range_filter == 'today':
            orders = orders.filter(created_at__date=today)
        elif range_filter == 'month':
            orders = orders.filter(created_at__year=today.year, created_at__month=today.month)

        paginator = OrdersPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class AllOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        orders = Order.objects.all().order_by('-created_at')
        paginator = OrdersPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)