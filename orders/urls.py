# orders/urls.py

from django.urls import path
from .views import (
    PlaceOrderView,
    MyOrdersView,
    OrderDetailView,
    UpdateOrderStatusView,
    RestaurantOrdersView,
    AllOrdersView,
)

urlpatterns = [
    path('place/', PlaceOrderView.as_view(), name='place_order'),
    path('my/', MyOrdersView.as_view(), name='my_orders'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/status/', UpdateOrderStatusView.as_view(), name='update_order_status'),
    path('restaurant/<int:restaurant_id>/', RestaurantOrdersView.as_view(), name='restaurant_orders'),
    path('all/', AllOrdersView.as_view(), name='all_orders'),
]