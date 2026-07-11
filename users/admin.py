# users/admin.py — Register User model on Django admin panel

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Columns shown in the user list view
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'username']
    ordering = ['-date_joined']

    # Add 'role' and 'phone' to the default UserAdmin fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('FoodCourt Info', {
            'fields': ('role', 'phone', 'avatar')
        }),
    )

    # Fields shown when creating a new user from admin
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('FoodCourt Info', {
            'fields': ('email', 'first_name', 'last_name', 'role', 'phone')
        }),
    )