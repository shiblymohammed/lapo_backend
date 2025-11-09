from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from orders.models import Order, OrderItem
from authentication.models import CustomUser
from products.models import Package, Campaign
from django.contrib.contenttypes.models import ContentType


class AnalyticsService:
    """Service for calculating analytics and business metrics"""
    
    @staticmethod
    def get_revenue_metrics(start_date=None, end_date=None):
        """
        Calculate revenue metrics for a date range.
        
        Args:
            start_date: Start date for filtering (datetime object)
            end_date: End date for filtering (datetime object)
            
        Returns:
            dict: Revenue metrics including total_revenue, order_count, average_order_value
        """
        # Build base queryset for paid orders
        queryset = Order.objects.filter(
            status__in=['ready_for_processing', 'assigned', 'in_progress', 'completed'],
            payment_completed_at__isnull=False
        )
        
        # Apply date filters if provided
        if start_date:
            queryset = queryset.filter(payment_completed_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_completed_at__lte=end_date)
        
        # Calculate metrics
        aggregates = queryset.aggregate(
            total_revenue=Sum('total_amount'),
            order_count=Count('id'),
            average_order_value=Avg('total_amount')
        )
        
        return {
            'total_revenue': float(aggregates['total_revenue'] or 0),
            'order_count': aggregates['order_count'] or 0,
            'average_order_value': float(aggregates['average_order_value'] or 0),
        }
    
    @staticmethod
    def get_top_products(limit=5, start_date=None, end_date=None):
        """
        Get best-selling products by quantity sold.
        
        Args:
            limit: Number of top products to return
            start_date: Start date for filtering (datetime object)
            end_date: End date for filtering (datetime object)
            
        Returns:
            list: Top products with name, quantity_sold, and revenue
        """
        # Build base queryset for order items from paid orders
        queryset = OrderItem.objects.filter(
            order__status__in=['ready_for_processing', 'assigned', 'in_progress', 'completed'],
            order__payment_completed_at__isnull=False
        ).select_related('order')  # Optimize query with select_related
        
        # Apply date filters if provided
        if start_date:
            queryset = queryset.filter(order__payment_completed_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(order__payment_completed_at__lte=end_date)
        
        # Get content types for Package and Campaign
        package_ct = ContentType.objects.get_for_model(Package)
        campaign_ct = ContentType.objects.get_for_model(Campaign)
        
        # Aggregate by product (content_type + object_id)
        product_stats = queryset.values(
            'content_type', 'object_id'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('price') * F('quantity'))
        ).order_by('-total_quantity')[:limit]
        
        # Batch fetch all products to avoid N+1 queries
        package_ids = [stat['object_id'] for stat in product_stats if stat['content_type'] == package_ct.id]
        campaign_ids = [stat['object_id'] for stat in product_stats if stat['content_type'] == campaign_ct.id]
        
        # Fetch all packages and campaigns in bulk
        packages = {p.id: p for p in Package.objects.filter(id__in=package_ids)}
        campaigns = {c.id: c for c in Campaign.objects.filter(id__in=campaign_ids)}
        
        # Enrich with product details
        top_products = []
        for stat in product_stats:
            content_type_id = stat['content_type']
            object_id = stat['object_id']
            
            # Get product name based on content type
            product_name = 'Unknown Product'
            product_type = 'unknown'
            
            if content_type_id == package_ct.id:
                package = packages.get(object_id)
                if package:
                    product_name = package.name
                    product_type = 'package'
            elif content_type_id == campaign_ct.id:
                campaign = campaigns.get(object_id)
                if campaign:
                    product_name = campaign.name
                    product_type = 'campaign'
            
            top_products.append({
                'product_id': object_id,
                'product_type': product_type,
                'product_name': product_name,
                'quantity_sold': stat['total_quantity'],
                'revenue': float(stat['total_revenue'] or 0)
            })
        
        return top_products
    
    @staticmethod
    def get_staff_performance(start_date=None, end_date=None):
        """
        Calculate staff performance metrics.
        
        Args:
            start_date: Start date for filtering (datetime object)
            end_date: End date for filtering (datetime object)
            
        Returns:
            list: Staff members with assigned_orders, completed_orders, completion_rate
        """
        # Get all staff and admin users
        staff_users = CustomUser.objects.filter(role__in=['staff', 'admin']).only(
            'id', 'username', 'phone_number', 'role'
        )
        
        # Build base queryset for orders
        orders_queryset = Order.objects.all()
        
        # Apply date filters if provided
        if start_date:
            orders_queryset = orders_queryset.filter(updated_at__gte=start_date)
        if end_date:
            orders_queryset = orders_queryset.filter(updated_at__lte=end_date)
        
        # Aggregate order counts per staff member in a single query
        staff_stats = orders_queryset.values('assigned_to').annotate(
            assigned_count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed'))
        )
        
        # Create a lookup dictionary for staff stats
        stats_lookup = {stat['assigned_to']: stat for stat in staff_stats if stat['assigned_to']}
        
        performance_data = []
        
        for staff in staff_users:
            # Get stats from lookup or use defaults
            stats = stats_lookup.get(staff.id, {'assigned_count': 0, 'completed_count': 0})
            assigned_count = stats['assigned_count']
            completed_count = stats['completed_count']
            
            # Calculate completion rate
            completion_rate = 0
            if assigned_count > 0:
                completion_rate = (completed_count / assigned_count) * 100
            
            performance_data.append({
                'staff_id': staff.id,
                'staff_name': staff.username,
                'phone_number': staff.phone_number,
                'role': staff.role,
                'assigned_orders': assigned_count,
                'completed_orders': completed_count,
                'completion_rate': round(completion_rate, 2)
            })
        
        # Sort by assigned orders (descending)
        performance_data.sort(key=lambda x: x['assigned_orders'], reverse=True)
        
        return performance_data
    
    @staticmethod
    def get_order_status_distribution(start_date=None, end_date=None):
        """
        Get count of orders by status.
        
        Args:
            start_date: Start date for filtering (datetime object)
            end_date: End date for filtering (datetime object)
            
        Returns:
            dict: Order counts by status
        """
        # Build base queryset
        queryset = Order.objects.all()
        
        # Apply date filters if provided
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Count by status
        status_counts = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Convert to dictionary with readable labels
        distribution = {}
        for item in status_counts:
            status = item['status']
            count = item['count']
            
            # Get readable label
            status_label = dict(Order.STATUS_CHOICES).get(status, status)
            
            distribution[status] = {
                'label': status_label,
                'count': count
            }
        
        return distribution
    
    @staticmethod
    def get_revenue_trend(months=12):
        """
        Get monthly revenue data for the last N months.
        
        Args:
            months: Number of months to include (default 12)
            
        Returns:
            list: Monthly revenue data with month and revenue
        """
        # Calculate start date (N months ago)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # Get paid orders in date range
        orders = Order.objects.filter(
            status__in=['ready_for_processing', 'assigned', 'in_progress', 'completed'],
            payment_completed_at__isnull=False,
            payment_completed_at__gte=start_date,
            payment_completed_at__lte=end_date
        )
        
        # Group by month and sum revenue
        from django.db.models.functions import TruncMonth
        
        monthly_data = orders.annotate(
            month=TruncMonth('payment_completed_at')
        ).values('month').annotate(
            revenue=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('month')
        
        # Format results
        trend_data = []
        for item in monthly_data:
            trend_data.append({
                'month': item['month'].strftime('%Y-%m'),
                'month_label': item['month'].strftime('%B %Y'),
                'revenue': float(item['revenue'] or 0),
                'order_count': item['order_count']
            })
        
        return trend_data
    
    @staticmethod
    def get_conversion_rate(start_date=None, end_date=None):
        """
        Calculate conversion rate from cart to completed orders.
        
        Args:
            start_date: Start date for filtering (datetime object)
            end_date: End date for filtering (datetime object)
            
        Returns:
            dict: Conversion metrics
        """
        # Build base queryset
        all_orders = Order.objects.all()
        
        # Apply date filters if provided
        if start_date:
            all_orders = all_orders.filter(created_at__gte=start_date)
        if end_date:
            all_orders = all_orders.filter(created_at__lte=end_date)
        
        # Count total orders and completed payments
        total_orders = all_orders.count()
        paid_orders = all_orders.filter(
            payment_completed_at__isnull=False
        ).count()
        
        # Calculate conversion rate
        conversion_rate = 0
        if total_orders > 0:
            conversion_rate = (paid_orders / total_orders) * 100
        
        return {
            'total_orders': total_orders,
            'paid_orders': paid_orders,
            'conversion_rate': round(conversion_rate, 2)
        }
    
    @staticmethod
    def get_year_over_year_growth(current_start, current_end, previous_start, previous_end):
        """
        Calculate year-over-year growth for revenue.
        
        Args:
            current_start: Start date for current period
            current_end: End date for current period
            previous_start: Start date for previous period
            previous_end: End date for previous period
            
        Returns:
            dict: Growth metrics
        """
        # Get current period revenue
        current_metrics = AnalyticsService.get_revenue_metrics(current_start, current_end)
        current_revenue = current_metrics['total_revenue']
        
        # Get previous period revenue
        previous_metrics = AnalyticsService.get_revenue_metrics(previous_start, previous_end)
        previous_revenue = previous_metrics['total_revenue']
        
        # Calculate growth percentage
        growth_percentage = 0
        if previous_revenue > 0:
            growth_percentage = ((current_revenue - previous_revenue) / previous_revenue) * 100
        
        return {
            'current_revenue': current_revenue,
            'previous_revenue': previous_revenue,
            'growth_percentage': round(growth_percentage, 2),
            'growth_amount': current_revenue - previous_revenue
        }
