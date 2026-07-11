# menu/serializers.py

from rest_framework import serializers
from .models import MenuItem, MenuCategory


class MenuCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = MenuCategory
        fields = ['id', 'name', 'order']


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'image',
            'availability', 'is_featured', 'prep_time_minutes',
            'category', 'category_name', 'restaurant', 'created_at',
            'image_url'
        ]

    def get_image_url(self, obj):
        return obj.image


class MenuItemCreateSerializer(serializers.ModelSerializer):
    """Accepts image URL from frontend (Supabase)"""

    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'price', 'image',
            'availability', 'is_featured', 'prep_time_minutes', 'category'
        ]