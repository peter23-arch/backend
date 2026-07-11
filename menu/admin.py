# menu/admin.py — Register MenuItem and MenuCategory on Django admin panel

from django.contrib import admin
from .models import MenuItem, MenuCategory


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'order']
    list_filter = ['restaurant']
    search_fields = ['name', 'restaurant__name']
    ordering = ['restaurant', 'order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'category', 'price', 'availability', 'is_featured', 'created_at']
    list_filter = ['availability', 'is_featured', 'restaurant']
    search_fields = ['name', 'restaurant__name', 'category__name']
    ordering = ['-created_at']

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('restaurant', 'category', 'name', 'description')
        }),
        ('Pricing & Timing', {
            'fields': ('price', 'prep_time_minutes')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Availability', {
            'fields': ('availability', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )