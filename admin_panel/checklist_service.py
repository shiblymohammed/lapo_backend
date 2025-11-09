from orders.models import OrderChecklist, ChecklistItem
from products.models import ChecklistTemplateItem
from django.contrib.contenttypes.models import ContentType


class ChecklistService:
    """Service for generating and managing order checklists"""
    
    @staticmethod
    def generate_checklist_for_order(order):
        """
        Generate a checklist for an order based on template items from products.
        If no templates exist, falls back to default checklist generation.
        Returns the created OrderChecklist instance.
        """
        # Create or get checklist
        checklist, created = OrderChecklist.objects.get_or_create(order=order)
        
        # If checklist already exists with items, return it
        if not created and checklist.items.exists():
            return checklist
        
        # Try to generate checklist from templates
        template_items = ChecklistService._get_template_items_for_order(order)
        
        if template_items:
            # Create checklist items from templates
            ChecklistItem.objects.bulk_create([
                ChecklistItem(
                    checklist=checklist,
                    template_item=template_item,
                    description=template_item.name,
                    order_index=template_item.order,
                    is_optional=template_item.is_optional
                )
                for template_item in template_items
            ])
        else:
            # Fallback to default checklist generation
            checklist_items = ChecklistService._generate_checklist_items(order)
            
            # Create checklist items
            ChecklistItem.objects.bulk_create([
                ChecklistItem(
                    checklist=checklist,
                    description=item['description'],
                    order_index=item['order_index'],
                    is_optional=item.get('is_optional', False)
                )
                for item in checklist_items
            ])
        
        return checklist
    
    @staticmethod
    def _get_template_items_for_order(order):
        """
        Get all checklist template items for products in the order.
        Returns a list of ChecklistTemplateItem objects ordered by their order field.
        """
        template_items = []
        
        for order_item in order.items.all():
            content_type = order_item.content_type
            object_id = order_item.object_id
            
            # Get template items for this product
            items = ChecklistTemplateItem.objects.filter(
                content_type=content_type,
                object_id=object_id
            ).order_by('order')
            
            template_items.extend(items)
        
        # Re-sort all items by order to maintain proper sequence
        template_items.sort(key=lambda x: x.order)
        
        return template_items
    
    @staticmethod
    def _generate_checklist_items(order):
        """
        Generate checklist items based on order contents.
        This creates a comprehensive task list based on package/campaign types.
        """
        checklist_items = []
        index = 0
        
        # Initial review tasks
        checklist_items.append({
            'description': f'Review order {order.order_number} details and requirements',
            'order_index': index
        })
        index += 1
        
        checklist_items.append({
            'description': f'Contact customer at {order.user.phone_number} to confirm order',
            'order_index': index
        })
        index += 1
        
        # Generate tasks for each order item
        for order_item in order.items.all():
            item_name = str(order_item.content_object) if order_item.content_object else 'Item'
            item_type = order_item.content_type.model
            quantity = order_item.quantity
            
            # Review resources
            checklist_items.append({
                'description': f'Review uploaded resources for {item_name} (Qty: {quantity})',
                'order_index': index
            })
            index += 1
            
            # Package-specific tasks
            if item_type == 'package':
                checklist_items.extend(ChecklistService._generate_package_tasks(item_name, quantity, index))
                index += len(ChecklistService._generate_package_tasks(item_name, quantity, index))
            
            # Campaign-specific tasks
            elif item_type == 'campaign':
                checklist_items.extend(ChecklistService._generate_campaign_tasks(item_name, quantity, index))
                index += len(ChecklistService._generate_campaign_tasks(item_name, quantity, index))
        
        # Final tasks
        checklist_items.append({
            'description': 'Conduct final quality check on all deliverables',
            'order_index': index
        })
        index += 1
        
        checklist_items.append({
            'description': 'Contact customer for final approval and feedback',
            'order_index': index
        })
        index += 1
        
        checklist_items.append({
            'description': 'Mark order as completed and archive documentation',
            'order_index': index
        })
        
        return checklist_items
    
    @staticmethod
    def _generate_package_tasks(package_name, quantity, start_index):
        """Generate tasks specific to package items"""
        tasks = []
        index = start_index
        
        tasks.append({
            'description': f'Prepare all components for {package_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Customize materials with candidate information for {package_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Schedule delivery/installation for {package_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Coordinate with technical team for setup of {package_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Complete delivery and setup of {package_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Provide training/documentation for {package_name}',
            'order_index': index
        })
        
        return tasks
    
    @staticmethod
    def _generate_campaign_tasks(campaign_name, quantity, start_index):
        """Generate tasks specific to campaign items"""
        tasks = []
        index = start_index
        
        tasks.append({
            'description': f'Schedule campaign execution for {campaign_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Coordinate with field team for {campaign_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Prepare campaign materials for {campaign_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Execute campaign activities for {campaign_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Document campaign execution and results for {campaign_name}',
            'order_index': index
        })
        index += 1
        
        tasks.append({
            'description': f'Provide campaign report to customer for {campaign_name}',
            'order_index': index
        })
        
        return tasks
    
    @staticmethod
    def get_checklist_progress(checklist):
        """
        Calculate progress percentage for a checklist.
        Excludes optional items from the calculation.
        Returns a dict with progress information.
        """
        items = checklist.items.all()
        total_items = items.count()
        
        # Calculate progress excluding optional items
        required_items = items.filter(is_optional=False)
        total_required = required_items.count()
        
        if total_required == 0:
            # If no required items, use all items for calculation
            if total_items == 0:
                return {
                    'total_items': 0,
                    'completed_items': 0,
                    'required_items': 0,
                    'completed_required': 0,
                    'progress_percentage': 0
                }
            
            completed_items = items.filter(completed=True).count()
            progress_percentage = int((completed_items / total_items) * 100)
            
            return {
                'total_items': total_items,
                'completed_items': completed_items,
                'required_items': 0,
                'completed_required': completed_items,
                'progress_percentage': progress_percentage
            }
        
        # Calculate based on required items only
        completed_required = required_items.filter(completed=True).count()
        completed_items = items.filter(completed=True).count()
        progress_percentage = int((completed_required / total_required) * 100)
        
        return {
            'total_items': total_items,
            'completed_items': completed_items,
            'required_items': total_required,
            'completed_required': completed_required,
            'progress_percentage': progress_percentage
        }
    
    @staticmethod
    def update_order_status_based_on_checklist(order):
        """
        Update order status based on checklist completion.
        If all items are complete, mark order as completed.
        Otherwise, mark as in_progress.
        """
        try:
            checklist = order.checklist
            progress = ChecklistService.get_checklist_progress(checklist)
            
            if progress['progress_percentage'] == 100:
                if order.status != 'completed':
                    order.status = 'completed'
                    order.save()
                    return True  # Status changed to completed
            elif order.status == 'assigned':
                order.status = 'in_progress'
                order.save()
            
            return False  # Status not changed to completed
            
        except OrderChecklist.DoesNotExist:
            return False
