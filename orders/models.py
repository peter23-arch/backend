# orders/models.py — Order and OrderItem models

from django.db import models
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP


class Order(models.Model):
    """A food order placed by a customer"""

    STATUS_CHOICES = (
        ('pending', 'Pending'),           # just placed
        ('confirmed', 'Confirmed'),       # restaurant confirmed
        ('preparing', 'Preparing'),       # kitchen is making it
        ('ready', 'Ready for Pickup'),    # customer can pick up
        ('completed', 'Completed'),       # picked up
        ('cancelled', 'Cancelled'),
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='orders'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_phone = models.CharField(max_length=20, null=True, blank=True)  # optional for pickup orders
    delivery_location = models.CharField(max_length=500,null=True, blank=True)  # optional for pickup orders
    notes = models.TextField(blank=True)  # special instructions from customer
    # Snapshot of the restaurant's fee percentage at the moment this order was placed
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.email}"

    def calculate_total(self):
        """Recalculate total from all order items"""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save()
    @property
    def fee_amount(self):
        return (self.total_amount * self.platform_fee_percent / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def net_amount(self):
        return self.total_amount - self.fee_amount


class OrderItem(models.Model):
    """A single line item within an order"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of order

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"