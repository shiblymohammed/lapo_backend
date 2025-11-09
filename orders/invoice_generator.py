"""
Invoice generation service using ReportLab
"""
from io import BytesIO
from datetime import datetime
from django.conf import settings
import os


class InvoiceGenerator:
    """Generate PDF invoices for orders"""
    
    def __init__(self):
        # Styles will be initialized when needed
        self.styles = None
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Import reportlab at function level to reduce initial memory footprint
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        
        self.styles = getSampleStyleSheet()
        
        # Company name style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a56db'),
            alignment=TA_CENTER,
            spaceAfter=6
        ))
        
        # Invoice title style
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#374151'),
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=6
        ))
        
        # Right aligned text
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT
        ))
        
        # Small text style
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.grey
        ))
    
    def generate_invoice(self, order):
        """
        Generate PDF invoice for an order
        
        Args:
            order: Order instance
            
        Returns:
            BytesIO buffer containing the PDF
        """
        # Import reportlab at function level to reduce initial memory footprint
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Spacer
        
        # Initialize styles if not already done
        if self.styles is None:
            self._setup_custom_styles()
        
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build document content
        story = []
        
        # Add company header
        story.extend(self._build_header())
        story.append(Spacer(1, 0.3*inch))
        
        # Add invoice title and details
        story.extend(self._build_invoice_details(order))
        story.append(Spacer(1, 0.3*inch))
        
        # Add customer information
        story.extend(self._build_customer_info(order))
        story.append(Spacer(1, 0.3*inch))
        
        # Add order items table
        story.extend(self._build_items_table(order))
        story.append(Spacer(1, 0.2*inch))
        
        # Add payment information
        story.extend(self._build_payment_info(order))
        story.append(Spacer(1, 0.3*inch))
        
        # Add footer
        story.extend(self._build_footer())
        
        # Build PDF
        doc.build(story)
        
        # Reset buffer position
        buffer.seek(0)
        return buffer
    
    def _build_invoice_details(self, order):
        """Build invoice details section"""
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import Table, TableStyle, Paragraph
        
        elements = []
        
        # Invoice title
        title = Paragraph("INVOICE", self.styles['InvoiceTitle'])
        elements.append(title)
        
        # Get payment history
        payment_history = getattr(order, 'payment_history', None)
        
        # Invoice details table
        invoice_data = [
            ['Invoice Number:', payment_history.invoice_number if payment_history else f'INV-{order.order_number}'],
            ['Order Number:', order.order_number],
            ['Invoice Date:', payment_history.payment_date.strftime('%B %d, %Y') if payment_history else datetime.now().strftime('%B %d, %Y')],
            ['Order Date:', order.created_at.strftime('%B %d, %Y')],
        ]
        
        invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(invoice_table)
        
        return elements
    
    def _build_customer_info(self, order):
        """Build customer information section"""
        from reportlab.platypus import Paragraph
        
        elements = []
        
        # Section header
        header = Paragraph("Bill To:", self.styles['SectionHeader'])
        elements.append(header)
        
        # Customer details
        customer_info = f"""
        <b>{order.user.get_full_name() or order.user.username}</b><br/>
        Email: {order.user.email or 'N/A'}<br/>
        Phone: {getattr(order.user, 'phone_number', 'N/A')}
        """
        
        customer_para = Paragraph(customer_info, self.styles['Normal'])
        elements.append(customer_para)
        
        return elements
    
    def _build_header(self):
        """Build company header section"""
        from reportlab.platypus import Paragraph
        
        elements = []
        
        # Company name
        company_name = Paragraph("Election Cart", self.styles['CompanyName'])
        elements.append(company_name)
        
        # Company tagline
        tagline = Paragraph(
            "Your Complete Election Campaign Solution",
            self.styles['Normal']
        )
        elements.append(tagline)
        
        return elements
    

    
    def _build_items_table(self, order):
        """Build order items table"""
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        
        elements = []
        
        # Section header
        header = Paragraph("Order Items:", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Table header
        table_data = [
            ['Item', 'Type', 'Quantity', 'Unit Price', 'Subtotal']
        ]
        
        # Add order items
        for item in order.items.all():
            item_name = str(item.content_object) if item.content_object else 'Unknown Item'
            item_type = item.content_type.model.capitalize()
            quantity = str(item.quantity)
            unit_price = f"₹{item.price:,.2f}"
            subtotal = f"₹{item.get_subtotal():,.2f}"
            
            table_data.append([
                item_name,
                item_type,
                quantity,
                unit_price,
                subtotal
            ])
        
        # Add total row
        table_data.append(['', '', '', 'Total:', f"₹{order.total_amount:,.2f}"])
        
        # Create table with purple theme
        items_table = Table(table_data, colWidths=[2.5*inch, 1*inch, 0.8*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            # Header row styling - Purple theme
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7C3AED')),  # Purple
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),
            ('ALIGN', (2, 1), (2, -2), 'CENTER'),
            ('ALIGN', (3, 1), (-1, -2), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 10),
            ('TOPPADDING', (0, 1), (-1, -2), 10),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F3F4F6')]),
            
            # Total row styling - Purple theme
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EDE9FE')),  # Light purple
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 13),
            ('ALIGN', (3, -1), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#7C3AED')),  # Purple
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#7C3AED')),
            ('TOPPADDING', (0, -1), (-1, -1), 14),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 14),
            
            # Grid
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#D1D5DB')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#7C3AED')),  # Purple border
        ]))
        
        elements.append(items_table)
        
        return elements
    
    def _build_payment_info(self, order):
        """Build payment information section"""
        from reportlab.platypus import Paragraph
        
        elements = []
        
        # Section header
        header = Paragraph("Payment Information:", self.styles['SectionHeader'])
        elements.append(header)
        
        # Get payment history
        payment_history = getattr(order, 'payment_history', None)
        
        if payment_history:
            payment_info = f"""
            <b>Payment Method:</b> {payment_history.payment_method}<br/>
            <b>Transaction ID:</b> {payment_history.transaction_id}<br/>
            <b>Payment Status:</b> {payment_history.get_status_display()}<br/>
            <b>Payment Date:</b> {payment_history.payment_date.strftime('%B %d, %Y at %I:%M %p')}<br/>
            <b>Amount Paid:</b> ₹{payment_history.amount:,.2f} {payment_history.currency}
            """
        else:
            payment_info = f"""
            <b>Payment Status:</b> {order.get_status_display()}<br/>
            <b>Amount:</b> ₹{order.total_amount:,.2f}
            """
        
        payment_para = Paragraph(payment_info, self.styles['Normal'])
        elements.append(payment_para)
        
        return elements
    
    def _build_footer(self):
        """Build invoice footer"""
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import Paragraph, Spacer
        
        elements = []
        
        # Thank you message
        thank_you = Paragraph(
            "<b>Thank you for your business!</b>",
            self.styles['Normal']
        )
        elements.append(thank_you)
        elements.append(Spacer(1, 0.2*inch))
        
        # Footer note
        footer_note = Paragraph(
            "This is a computer-generated invoice and does not require a signature.<br/>"
            "For any queries, please contact us at support@electioncart.com",
            ParagraphStyle(
                name='FooterNote',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
        )
        elements.append(footer_note)
        
        return elements
    
    def get_invoice_filename(self, order):
        """
        Generate invoice filename
        
        Args:
            order: Order instance
            
        Returns:
            str: Filename for the invoice
        """
        payment_history = getattr(order, 'payment_history', None)
        
        if payment_history:
            invoice_number = payment_history.invoice_number
            date_str = payment_history.payment_date.strftime('%Y%m%d')
        else:
            invoice_number = order.order_number
            date_str = datetime.now().strftime('%Y%m%d')
        
        return f"Invoice-{invoice_number}-{date_str}.pdf"
