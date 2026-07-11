# orders/views.py — Order placement and management

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from notifications.firebase import send_push_notification
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer


class PlaceOrderView(APIView):
    """Customer places a new order — notifies restaurant in real time"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save(customer=request.user)
            order_data = OrderSerializer(order, context={'request': request}).data

            # # Send real-time notification to the restaurant manager
            # channel_layer = get_channel_layer()
            # async_to_sync(channel_layer.group_send)(
            #     f'restaurant_{order.restaurant.id}_manager',
            #     {
            #         'type': 'new_order',
            #         'message': {
            #             'type': 'NEW_ORDER',
            #             'order': order_data,
            #         }
            #     }
            # )
            # Inside PlaceOrderView.post — add after the channel_layer group_send block

            # Push notification to restaurant manager
            
            manager = order.restaurant.manager
            if manager.fcm_token:
                send_push_notification(
                    token=manager.fcm_token,
                    title=f'🛎️ New Order — {order.restaurant.name}',
                    body=f'Order #{order.id} from {request.user.get_full_name() or request.user.username}',
                    data={'type': 'NEW_ORDER', 'order_id': str(order.id)},
                )

            return Response(order_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyOrdersView(APIView):
    """Customer sees only their own orders"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)


class OrderDetailView(APIView):
    """Get or update a single order — customer or restaurant manager"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        # Only the customer or the restaurant manager can see this order
        if order.customer != request.user and order.restaurant.manager != request.user and not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)


class UpdateOrderStatusView(APIView):
    """Restaurant manager updates order status — notifies customer in real time"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        # Only restaurant manager or admin can update status
        if order.restaurant.manager != request.user and not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']

        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save()

        order_data = OrderSerializer(order, context={'request': request}).data

        # Notify the customer that their order status changed
        # channel_layer = get_channel_layer()
        # async_to_sync(channel_layer.group_send)(
        #     f'user_{order.customer.id}',
        #     {
        #         'type': 'order_update',
        #         'message': {
        #             'type': 'ORDER_STATUS_UPDATE',
        #             'order': order_data,
        #         }
        #     }
        # )
        # Push notification to customer
            
        customer = order.customer
        if customer.fcm_token:
            send_push_notification(
                token=customer.fcm_token,
                title=f'📦 Order Update — {order.restaurant.name}',
                body=f'Your order #{order.id} is now: {order.get_status_display()}',
                data={'type': 'ORDER_UPDATE', 'order_id': str(order.id)},
            )

        return Response(order_data)


class RestaurantOrdersView(APIView):
    """Restaurant manager sees all orders for their restaurant"""
    permission_classes = [IsAuthenticated]

    def get(self, request, restaurant_id):
        from restaurants.models import Restaurant
        restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

        if restaurant.manager != request.user and not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)


class AllOrdersView(APIView):
    """Platform admin sees all orders across all restaurants"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        orders = Order.objects.all().order_by('-created_at')
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)