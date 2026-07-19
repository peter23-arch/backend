# reviews/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from notifications.firebase import send_push_notification
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer
from restaurants.models import Restaurant


class ReviewsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class RestaurantReviewsView(APIView):
    """Get reviews for a restaurant (public, paginated) or post one (authenticated)"""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, restaurant_id):
        reviews = Review.objects.filter(restaurant_id=restaurant_id).order_by('-created_at')
        paginator = ReviewsPagination()
        page = paginator.paginate_queryset(reviews, request)
        serializer = ReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, restaurant_id):
        existing = Review.objects.filter(customer=request.user, restaurant_id=restaurant_id).first()
        if existing:
            return Response({'error': 'You have already reviewed this restaurant.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['restaurant'] = restaurant_id

        serializer = ReviewCreateSerializer(data=data)
        if serializer.is_valid():
            review = serializer.save(customer=request.user)
            restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
            review_data = ReviewSerializer(review).data

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{restaurant.id}_manager',
                {'type': 'new_review', 'message': {'type': 'NEW_REVIEW', 'review': review_data, 'restaurant_id': restaurant.id}}
            )

            manager = restaurant.manager
            if manager and manager.fcm_token:
                preview = (review.comment[:80] + '…') if review.comment and len(review.comment) > 80 else (review.comment or 'No comment left')
                send_push_notification(
                    token=manager.fcm_token,
                    title=f'⭐ New Review — {restaurant.name}',
                    body=f'{review.rating}/5 — {preview}',
                    data={'type': 'NEW_REVIEW', 'restaurant_id': str(restaurant.id)},
                )

            return Response(review_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteReviewView(APIView):
    """Admin only — remove a review that violates business integrity"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, review_id):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        review = get_object_or_404(Review, pk=review_id)
        restaurant_id = review.restaurant_id
        review.delete()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'restaurant_{restaurant_id}_manager',
            {'type': 'review_deleted', 'message': {'type': 'REVIEW_DELETED', 'review_id': review_id, 'restaurant_id': restaurant_id}}
        )

        return Response({'message': 'Review deleted.'}, status=status.HTTP_200_OK)