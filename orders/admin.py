# orders/admin.py — Register Order and OrderItem on Django admin panel

from django.contrib import admin
from .models import Order, OrderItem


# Show order items inline within the order detail page
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # don't show empty extra rows
    readonly_fields = ['unit_price', 'subtotal']

    # subtotal is a property, so we expose it as a method
    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'restaurant', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'restaurant']
    search_fields = ['customer__email', 'restaurant__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']

    # Show the items directly inside the order page
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Info', {
            'fields': ('customer', 'restaurant', 'status', 'notes')
        }),
        ('Financials', {
            'fields': ('total_amount',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'unit_price']
    search_fields = ['order__id', 'menu_item__name']
    ordering = ['-order__created_at']