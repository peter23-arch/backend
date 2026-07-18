# restaurants/urls.py

from django.urls import path
from .views import (
    RestaurantListView,
    RestaurantDetailView,
    RestaurantSuspendView,
    MyRestaurantView,
    RestaurantDeleteView,
    AssignManagerView,
    RemoveManagerView,
)

urlpatterns = [
    path('', RestaurantListView.as_view(), name='restaurant_list'),
    path('<int:pk>/', RestaurantDetailView.as_view(), name='restaurant_detail'),
    path('<int:pk>/suspend/', RestaurantSuspendView.as_view(), name='restaurant_suspend'),
    path('<int:pk>/delete/', RestaurantDeleteView.as_view(), name='restaurant_delete'),
    path('<int:pk>/assign-manager/', AssignManagerView.as_view(), name='assign_manager'),
    path('<int:pk>/remove-manager/', RemoveManagerView.as_view(), name='remove_manager'),
    path('my-restaurant/', MyRestaurantView.as_view(), name='my_restaurant'),
]