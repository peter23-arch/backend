# restaurants/models.py — Restaurant model

from django.db import models
from django.conf import settings


class Restaurant(models.Model):
    """A registered restaurant on the platform"""

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval'),
    )

    # The manager who owns this restaurant
    manager = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='restaurant'
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    # Cover photo shown on cards
    cover_image = models.URLField(blank=True, null=True)
    logo = models.URLField(blank=True, null=True)

    cuisine_type = models.CharField(max_length=100, blank=True)
    opening_hours = models.CharField(max_length=200, blank=True, default='9AM - 10PM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # For platform admin to toggle
    is_open = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0.0

    @property
    def total_reviews(self):
        return self.reviews.count()