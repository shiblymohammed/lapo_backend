"""
Celery tasks for order processing
"""
from celery import shared_task
from django.core.files.base import ContentFile
from .invoice_generator import InvoiceGenerator
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_invoice_async(self, order_id):
    """
    Generate invoice PDF for an order asynchronously
    
    Args:
        order_id: ID of the order to generate invoice for
        
    Returns:
        dict: Status and message
    """
    try:
        from .models import Order, PaymentHistory
        
        # Get the order
        order = Order.objects.select_related(
            'user', 'payment_history'
        ).prefetch_related('items').get(id=order_id)
        
        # Check if payment history exists
        if not hasattr(order, 'payment_history'):
            logger.error(f"No payment history found for order {order_id}")
            return {
                'status': 'error',
                'message': 'No payment history found for this order'
            }
        
        payment_history = order.payment_history
        
        # Generate invoice PDF
        invoice_generator = InvoiceGenerator()
        pdf_buffer = invoice_generator.generate_invoice(order)
        
        # Update payment history with invoice generation timestamp
        from django.utils import timezone
        payment_history.invoice_generated_at = timezone.now()
        payment_history.save()
        
        logger.info(f"Invoice generated successfully for order {order_id}")
        
        return {
            'status': 'success',
            'message': f'Invoice generated for order {order.order_number}',
            'invoice_number': payment_history.invoice_number
        }
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {
            'status': 'error',
            'message': f'Order {order_id} not found'
        }
    except Exception as exc:
        logger.error(f"Error generating invoice for order {order_id}: {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
