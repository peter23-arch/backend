# reviews/urls.py

from django.urls import path
from .views import RestaurantReviewsView

urlpatterns = [
    path('<int:restaurant_id>/', RestaurantReviewsView.as_view(), name='restaurant_reviews'),
]