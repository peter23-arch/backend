# restaurants/serializers.py

from rest_framework import serializers
from .models import Restaurant
from users.serializers import UserSerializer


class RestaurantSerializer(serializers.ModelSerializer):
    """Full restaurant data including image URLs and ratings"""


    average_rating = serializers.FloatField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    manager_info = UserSerializer(source='manager', read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'address', 'phone', 'email',
            'cover_image', 'logo', 'cuisine_type', 'opening_hours',
            'status', 'is_open', 'average_rating', 'total_reviews',
            'cover_image_url', 'logo_url',
            'manager_info', 'created_at'
        ]

    # def get_cover_image_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.cover_image and request:
    #         return request.build_absolute_uri(obj.cover_image.url)
    #     return None

    # def get_logo_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.logo and request:
    #         return request.build_absolute_uri(obj.logo.url)
    #     return None

    def get_cover_image_url(self, obj):
        return obj.cover_image

    def get_logo_url(self, obj):
        return obj.logo


class RestaurantCreateSerializer(serializers.ModelSerializer):
    """Used when creating/updating a restaurant"""

    class Meta:
        model = Restaurant
        fields = [
            'name', 'description', 'address', 'phone', 'email',
            'cover_image', 'logo', 'cuisine_type', 'opening_hours', 'is_open'
        ]