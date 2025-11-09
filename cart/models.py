from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from authentication.models import CustomUser


class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.phone_number}"
    
    def get_total(self):
        """Calculate total price of all items in cart"""
        total = 0
        for item in self.items.all():
            if item.content_object:
                total += item.content_object.price * item.quantity
        return total
    
    def get_item_count(self):
        """Get total number of items in cart"""
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'content_type', 'object_id']

    def __str__(self):
        return f"{self.content_object} x{self.quantity}"
    
    def get_subtotal(self):
        """Calculate subtotal for this cart item"""
        if self.content_object:
            return self.content_object.price * self.quantity
        return 0
