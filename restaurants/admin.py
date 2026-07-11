# restaurants/admin.py — Register Restaurant model on Django admin panel

from django.contrib import admin
from .models import Restaurant


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    # Columns in the list view
    list_display = ['name', 'manager', 'cuisine_type', 'status', 'is_open', 'average_rating', 'created_at']
    list_filter = ['status', 'is_open', 'cuisine_type']
    search_fields = ['name', 'address', 'manager__email']
    ordering = ['-created_at']

    # Make average_rating readable in detail view
    readonly_fields = ['created_at', 'updated_at']

    # Group fields neatly in the detail view
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'manager', 'description', 'cuisine_type')
        }),
        ('Contact', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Media', {
            'fields': ('cover_image', 'logo')
        }),
        ('Status', {
            'fields': ('status', 'is_open', 'opening_hours')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # hidden by default, click to expand
        }),
    )