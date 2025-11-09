import razorpay
from django.conf import settings
import hmac
import hashlib


class RazorpayClient:
    """
    Razorpay client service for payment processing.
    """
    
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    
    def create_order(self, amount, currency='INR', receipt=None):
        """
        Create a Razorpay order.
        
        Args:
            amount: Amount in smallest currency unit (paise for INR)
            currency: Currency code (default: INR)
            receipt: Order receipt/reference number
        
        Returns:
            dict: Razorpay order details
        """
        data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': currency,
            'receipt': receipt or '',
            'payment_capture': 1  # Auto capture payment
        }
        
        return self.client.order.create(data=data)
    
    def verify_payment_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify Razorpay payment signature for security.
        
        Args:
            razorpay_order_id: Razorpay order ID
            razorpay_payment_id: Razorpay payment ID
            razorpay_signature: Signature to verify
        
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Generate signature
            message = f"{razorpay_order_id}|{razorpay_payment_id}"
            generated_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(generated_signature, razorpay_signature)
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False
    
    def fetch_payment(self, payment_id):
        """
        Fetch payment details from Razorpay.
        
        Args:
            payment_id: Razorpay payment ID
        
        Returns:
            dict: Payment details
        """
        return self.client.payment.fetch(payment_id)
    
    def fetch_order(self, order_id):
        """
        Fetch order details from Razorpay.
        
        Args:
            order_id: Razorpay order ID
        
        Returns:
            dict: Order details
        """
        return self.client.order.fetch(order_id)


# Singleton instance
razorpay_client = RazorpayClient()
