# notifications/models.py
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """User notification"""
    
    NOTIFICATION_TYPES = (
        ('NEW_ORDER', 'New Order'),
        ('ORDER_STATUS_UPDATE', 'Order Status Update'),
        ('NEW_MENU_ITEM', 'New Menu Item'),
        ('ORDER_READY', 'Order Ready'),
        ('ORDER_PICKED_UP', 'Order Picked Up'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)  # Store additional data like order_id
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} - {self.user.email}"