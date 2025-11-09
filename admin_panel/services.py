from authentication.models import CustomUser
from orders.models import Order
from .models import Notification


class NotificationService:
    """Service for creating and managing notifications"""
    
    @staticmethod
    def notify_admins_new_order(order):
        """
        Send notification to all admin users when a new order is ready for processing.
        This is called when all resources are uploaded.
        """
        admin_users = CustomUser.objects.filter(role='admin')
        
        notifications = []
        for admin in admin_users:
            notification = Notification(
                user=admin,
                notification_type='new_order',
                title='New Order Ready for Processing',
                message=f'Order {order.order_number} from {order.user.phone_number} is ready for processing. Total: ₹{order.total_amount}',
                order=order
            )
            notifications.append(notification)
        
        # Bulk create for efficiency
        Notification.objects.bulk_create(notifications)
        
        return len(notifications)
    
    @staticmethod
    def notify_staff_order_assigned(order, staff_user):
        """
        Notify staff member when an order is assigned to them.
        """
        notification = Notification.objects.create(
            user=staff_user,
            notification_type='order_assigned',
            title='New Order Assigned',
            message=f'Order {order.order_number} has been assigned to you. Total items: {order.get_total_items()}',
            order=order
        )
        
        return notification
    
    @staticmethod
    def notify_admins_progress_update(order, progress_percentage):
        """
        Notify admin users when there's progress on an order.
        """
        admin_users = CustomUser.objects.filter(role='admin')
        
        notifications = []
        for admin in admin_users:
            notification = Notification(
                user=admin,
                notification_type='progress_update',
                title='Order Progress Update',
                message=f'Order {order.order_number} is now {progress_percentage}% complete.',
                order=order
            )
            notifications.append(notification)
        
        Notification.objects.bulk_create(notifications)
        
        return len(notifications)
    
    @staticmethod
    def notify_admins_order_completed(order):
        """
        Notify admin users when an order is completed.
        """
        admin_users = CustomUser.objects.filter(role='admin')
        
        notifications = []
        for admin in admin_users:
            notification = Notification(
                user=admin,
                notification_type='order_completed',
                title='Order Completed',
                message=f'Order {order.order_number} has been completed by {order.assigned_to.phone_number if order.assigned_to else "staff"}.',
                order=order
            )
            notifications.append(notification)
        
        Notification.objects.bulk_create(notifications)
        
        return len(notifications)
    
    @staticmethod
    def get_user_notifications(user, unread_only=False):
        """
        Get notifications for a specific user.
        """
        queryset = Notification.objects.filter(user=user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        return queryset
    
    @staticmethod
    def mark_as_read(notification_id, user):
        """
        Mark a notification as read.
        """
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save()
            return notification
        except Notification.DoesNotExist:
            return None
    
    @staticmethod
    def mark_all_as_read(user):
        """
        Mark all notifications as read for a user.
        """
        count = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return count
