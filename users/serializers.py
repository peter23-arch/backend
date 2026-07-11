# users/serializers.py — Serialize user data for API responses

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Handles new user registration"""

    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'password', 'password_confirm', 'phone', 'role']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        username = (validated_data.get('username') or '').strip()
        if not username:
            email = validated_data.get('email', '')
            base_username = slugify(email.split('@')[0]) or 'user'
            candidate = base_username
            index = 1
            while User.objects.filter(username=candidate).exists():
                candidate = f"{base_username}{index}"
                index += 1
            validated_data['username'] = candidate
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """General purpose user serializer"""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'role', 'phone', 'avatar_url', 'created_at',"avatar"]

    def get_avatar_url(self, obj):
        """Return the avatar URL"""
        return obj.avatar


class UserUpdateSerializer(serializers.ModelSerializer):
    """For updating profile info - now accepts avatar URL string instead of file"""
    avatar_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'avatar', 'avatar_url']
    
    def get_avatar_url(self, obj):
        """Return the avatar URL"""
        return obj.avatar
class ChangePasswordSerializer(serializers.Serializer):
    """Validates password change — requires current password"""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
    confirm_new_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data