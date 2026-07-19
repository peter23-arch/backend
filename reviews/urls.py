# reviews/urls.py

from django.urls import path
from .views import RestaurantReviewsView, DeleteReviewView

urlpatterns = [
    path('<int:restaurant_id>/', RestaurantReviewsView.as_view(), name='restaurant_reviews'),
    path('delete/<int:review_id>/', DeleteReviewView.as_view(), name='delete_review'),
]