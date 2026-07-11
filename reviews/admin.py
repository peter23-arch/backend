# reviews/admin.py — Register Review model on Django admin panel

from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['customer', 'restaurant', 'rating', 'created_at']
    list_filter = ['rating', 'restaurant']
    search_fields = ['customer__email', 'restaurant__name', 'comment']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Review Info', {
            'fields': ('customer', 'restaurant', 'rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )