# restaurants/urls.py

from django.urls import path
from .views import (
    RestaurantListView,
    RestaurantDetailView,
    RestaurantSuspendView,
    MyRestaurantView,
    RestaurantDeleteView,
)

urlpatterns = [
    path('', RestaurantListView.as_view(), name='restaurant_list'),
    path('<int:pk>/', RestaurantDetailView.as_view(), name='restaurant_detail'),
    path('<int:pk>/suspend/', RestaurantSuspendView.as_view(), name='restaurant_suspend'),
    path('<int:pk>/delete/', RestaurantDeleteView.as_view(), name='restaurant_delete'),  # add this
    path('my-restaurant/', MyRestaurantView.as_view(), name='my_restaurant'),
]