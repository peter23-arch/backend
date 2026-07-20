# orders/serializers.py

from rest_framework import serializers
from .models import Order, OrderItem
from menu.serializers import MenuItemSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_image_url = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'menu_item_image_url',
                  'quantity', 'unit_price', 'subtotal']

    def get_menu_item_image_url(self, obj):
        if obj.menu_item.image:
            if obj.menu_item.image.startswith(('http://', 'https://')):
                return obj.menu_item.image
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.menu_item.image)
            return obj.menu_item.image
        return None


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    """Full order with all items — includes fee breakdown for manager/admin visibility"""

    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    fee_amount = serializers.SerializerMethodField()
    net_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'customer_email', 'restaurant_name',
            'restaurant', 'status', 'status_display', 'total_amount',
            'delivery_phone', 'delivery_location', 'notes',
            'platform_fee_percent', 'fee_amount', 'net_amount',
            'items', 'created_at', 'updated_at'
        ]

    def get_fee_amount(self, obj):
        return str(obj.fee_amount)

    def get_net_amount(self, obj):
        return str(obj.net_amount)


class OrderCreateSerializer(serializers.ModelSerializer):
    """Place a new order — platform_fee_percent is NOT client-settable,
    it's snapshotted server-side from the restaurant's current fee."""

    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ['restaurant', 'notes', 'delivery_phone', 'delivery_location', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            menu_item = item_data['menu_item']
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                unit_price=menu_item.price
            )

        order.calculate_total()
        return order