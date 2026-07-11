# menu/models.py — Menu items for each restaurant

from django.db import models


class MenuCategory(models.Model):
    """Category grouping for menu items e.g. Starters, Mains, Drinks"""

    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='categories'
    )
    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)  # for display ordering

    def __str__(self):
        return f"{self.restaurant.name} — {self.name}"

    class Meta:
        ordering = ['order']


class MenuItem(models.Model):
    """Individual food/drink item on the menu"""

    AVAILABILITY_CHOICES = (
        ('available', 'Available Now'),
        ('later', 'Available Later'),
        ('unavailable', 'Not Available'),
    )

    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='menu_items'
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Food image — frontend will display via image_url
    image = models.URLField(blank=True, null=True)

    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default='available'
    )
    is_featured = models.BooleanField(default=False)
    prep_time_minutes = models.IntegerField(default=20)  # estimated prep time

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.restaurant.name}"

    class Meta:
        ordering = ['category', 'name']