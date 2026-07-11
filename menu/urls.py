# menu/urls.py

from django.urls import path
from .views import (
    MenuListView,
    MenuItemDetailView,
    MenuAvailabilityView,
    MenuCategoryListView,
)

urlpatterns = [
    # Get all menu items for a restaurant / add new item
    path('<int:restaurant_id>/', MenuListView.as_view(), name='menu_list'),

    # Update / delete a single item
    path('<int:restaurant_id>/items/<int:item_id>/', MenuItemDetailView.as_view(), name='menu_item_detail'),

    # Toggle availability
    path('<int:restaurant_id>/items/<int:item_id>/availability/', MenuAvailabilityView.as_view(), name='menu_availability'),

    # Categories
    path('<int:restaurant_id>/categories/', MenuCategoryListView.as_view(), name='menu_categories'),
]