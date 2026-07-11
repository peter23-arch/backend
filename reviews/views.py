# reviews/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer
from restaurants.models import Restaurant


class RestaurantReviewsView(APIView):
    """Get reviews for a restaurant (public) or post one (authenticated)"""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, restaurant_id):
        reviews = Review.objects.filter(restaurant_id=restaurant_id).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    def post(self, request, restaurant_id):
        # Check if user already reviewed this restaurant
        existing = Review.objects.filter(customer=request.user, restaurant_id=restaurant_id).first()
        if existing:
            return Response({'error': 'You have already reviewed this restaurant.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['restaurant'] = restaurant_id

        serializer = ReviewCreateSerializer(data=data)
        if serializer.is_valid():
            review = serializer.save(customer=request.user)
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)