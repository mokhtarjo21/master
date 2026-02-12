"""
Receipt Utilities
PDF generation and sending utilities
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from io import BytesIO
import os


def setup_arabic_font():
    """Setup Arabic font for PDF generation"""
    try:
        font_path = getattr(settings, 'PDF_ARABIC_FONT_PATH', None)
        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arabic', font_path))
            return 'Arabic'
    except:
        pass
    return 'Helvetica'


def generate_receipt_pdf(receipt):
    """Generate PDF for receipt"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Setup styles
    styles = getSampleStyleSheet()
    arabic_font = setup_arabic_font()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName=arabic_font
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        fontName=arabic_font
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        fontName=arabic_font,
        alignment=TA_RIGHT if receipt.payment.student.teacher.language == 'ar' else TA_LEFT
    )
    
    # Build content
    content = []
    
    # Header
    teacher_profile = getattr(receipt.payment.student.teacher, 'teacher_profile', None)
    center_name = teacher_profile.center_name if teacher_profile else receipt.payment.student.teacher.username
    
    content.append(Paragraph(center_name, title_style))
    content.append(Spacer(1, 12))
    
    # Receipt title
    content.append(Paragraph(receipt.title, header_style))
    content.append(Spacer(1, 12))
    
    # Receipt details
    receipt_data = [
        ['Receipt Number:', receipt.receipt_number],
        ['Date:', receipt.created_at.strftime('%Y-%m-%d')],
        ['Student:', receipt.payment.student.name],
        ['Student Code:', receipt.payment.student.code],
    ]
    
    if receipt.payment.period_start and receipt.payment.period_end:
        receipt_data.append([
            'Period:', 
            f"{receipt.payment.period_start} to {receipt.payment.period_end}"
        ])
    
    receipt_table = Table(receipt_data, colWidths=[2*inch, 3*inch])
    receipt_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), arabic_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    content.append(receipt_table)
    content.append(Spacer(1, 20))
    
    # Payment details
    content.append(Paragraph('Payment Details', header_style))
    
    payment_data = [
        ['Description', 'Amount'],
        [receipt.payment.get_payment_type_display(), f"{receipt.payment.amount:.2f}"],
    ]
    
    if receipt.payment.discount_amount > 0:
        payment_data.append([
            f"Discount ({receipt.payment.discount_reason})",
            f"-{receipt.payment.discount_amount:.2f}"
        ])
    
    payment_data.append(['Total Paid', f"{receipt.payment.amount_paid:.2f}"])
    
    if receipt.payment.remaining_amount > 0:
        payment_data.append(['Remaining', f"{receipt.payment.remaining_amount:.2f}"])
    
    payment_table = Table(payment_data, colWidths=[3*inch, 2*inch])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), arabic_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    content.append(payment_table)
    content.append(Spacer(1, 30))
    
    # Footer
    if receipt.payment.notes:
        content.append(Paragraph('Notes:', header_style))
        content.append(Paragraph(receipt.payment.notes, normal_style))
        content.append(Spacer(1, 20))
    
    # Signature area
    content.append(Spacer(1, 30))
    content.append(Paragraph('_' * 30, normal_style))
    content.append(Paragraph('Authorized Signature', normal_style))
    
    # Build PDF
    doc.build(content)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content


def send_receipt_email(receipt, email):
    """Send receipt via email"""
    subject = f"Payment Receipt - {receipt.receipt_number}"
    
    context = {
        'receipt': receipt,
        'student': receipt.payment.student,
        'payment': receipt.payment,
    }
    
    html_content = render_to_string('receipts/receipt_email.html', context)
    text_content = render_to_string('receipts/receipt_email.txt', context)
    
    email_message = EmailMessage(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
    )
    
    email_message.attach_alternative(html_content, "text/html")
    
    # Attach PDF
    if receipt.pdf_file:
        email_message.attach_file(receipt.pdf_file.path)
    
    email_message.send()


def send_receipt_whatsapp(receipt):
    """Send receipt via WhatsApp (placeholder for WhatsApp API integration)"""
    # This would integrate with WhatsApp Business API
    # For now, we'll just log the action
    
    student = receipt.payment.student
    whatsapp_number = student.whatsapp_number or student.phone
    
    if not whatsapp_number:
        raise ValueError("No WhatsApp number available for student")
    
    message = f"""
🧾 Payment Receipt

Receipt #: {receipt.receipt_number}
Student: {student.name}
Amount: {receipt.payment.amount_paid:.2f}
Date: {receipt.created_at.strftime('%Y-%m-%d')}

Thank you for your payment!
    """.strip()
    
    # TODO: Integrate with actual WhatsApp API
    # For now, create a notification record
    from notifications.models import Notification
    
    Notification.objects.create(
        recipient_type='student',
        recipient_id=student.id,
        title='Payment Receipt',
        message=message,
        notification_type='receipt',
        channel='whatsapp',
        status='pending'
    )
    
    return True


def generate_monthly_receipts(teacher, year, month):
    """Generate receipts for all monthly payments in a given month"""
    from payments.models import Payment
    from .models import Receipt
    
    # Get all paid monthly payments for the month
    monthly_payments = Payment.objects.filter(
        student__teacher=teacher,
        payment_type='monthly',
        status='paid',
        payment_date__year=year,
        payment_date__month=month
    ).exclude(receipt__isnull=False)  # Exclude payments that already have receipts
    
    receipts_created = []
    
    for payment in monthly_payments:
        receipt = Receipt.objects.create(
            payment=payment,
            receipt_type='monthly',
            title=f"Monthly Payment Receipt - {payment.student.name}",
            description=f"Payment for {payment.period_start} to {payment.period_end}"
        )
        receipts_created.append(receipt)
    
    return receipts_created


def bulk_generate_pdfs(receipts):
    """Bulk generate PDFs for multiple receipts"""
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    for receipt in receipts:
        try:
            if receipt.generate_pdf():
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Receipt {receipt.receipt_number}: {receipt.error_message}")
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Receipt {receipt.receipt_number}: {str(e)}")
    
    return results


def create_receipt_from_payment(payment):
    """Create receipt automatically when payment is made"""
    from .models import Receipt
    
    # Check if receipt already exists
    if hasattr(payment, 'receipt'):
        return payment.receipt
    
    # Create new receipt
    receipt = Receipt.objects.create(
        payment=payment,
        receipt_type='payment',
        title=f"Payment Receipt - {payment.student.name}",
        description=f"{payment.get_payment_type_display()} payment"
    )
    
    # Auto-generate PDF if enabled
    teacher_profile = getattr(payment.student.teacher, 'teacher_profile', None)
    if teacher_profile and teacher_profile.auto_receipts_enabled:
        receipt.generate_pdf()
    
    return receipt