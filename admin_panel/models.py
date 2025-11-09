from django.db import models
from authentication.models import CustomUser
from orders.models import Order


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_order', 'New Order'),
        ('order_assigned', 'Order Assigned'),
        ('progress_update', 'Progress Update'),
        ('order_completed', 'Order Completed'),
    ]
    
    user = models.ForeignKey(CustomUser, related_name='notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    order = models.ForeignKey(Order, related_name='notifications', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.user.phone_number}"
