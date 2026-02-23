"""
Student Cards PDF Generator
Generates a 3-column grid of student ID cards with QR codes (Arabic RTL layout)
"""
from io import BytesIO
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Image as RLImage,
    Paragraph, Spacer
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
import arabic_reshaper
from bidi.algorithm import get_display
import os
from django.conf import settings
from django.utils import timezone


# ─── Arabic text helper ───────────────────────────────────────────────────────

def ar(text):
    """Reshape + apply bidi so Arabic renders correctly in ReportLab."""
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


# ─── Font setup ───────────────────────────────────────────────────────────────

def _get_arabic_font():
    """Register and return Arabic font name."""
    font_name = 'ArabicCard'
    try:
        if font_name in pdfmetrics.getRegisteredFontNames():
            return font_name
        # Try configured path first
        font_path = getattr(settings, 'PDF_ARABIC_FONT_PATH', None)
        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            return font_name
        # Fallback: look for common fonts shipped with arabic-reshaper
        candidates = [
            os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'Amiri-Regular.ttf'),
            os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'Cairo-Regular.ttf'),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
    except Exception:
        pass
    return 'Helvetica'


# ─── QR code generation ───────────────────────────────────────────────────────

def _make_qr_image(data: str, size_px: int = 120) -> BytesIO:
    """Generate a QR code and return it as a BytesIO PNG."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white').convert('RGB')
    img = img.resize((size_px, size_px), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


# ─── Single card builder ──────────────────────────────────────────────────────

CARD_W = 6.1 * cm   # width of each card
CARD_H = 4.3 * cm   # height of each card
QR_SIZE = 2.8 * cm  # QR code size inside card

def _build_card(student, font_name: str) -> Table:
    """
    Build one student card as a ReportLab Table.
    Layout (RTL):
      [text col (right)] | [QR col (left)]
    """
    # ── Styles ──
    name_style = ParagraphStyle(
        'CardName', fontName=font_name, fontSize=9, leading=12,
        alignment=TA_RIGHT, textColor=colors.black
    )
    info_style = ParagraphStyle(
        'CardInfo', fontName=font_name, fontSize=6.5, leading=9,
        alignment=TA_RIGHT, textColor=colors.HexColor('#333333')
    )
    code_style = ParagraphStyle(
        'CardCode', fontName=font_name, fontSize=6, leading=8,
        alignment=TA_RIGHT, textColor=colors.HexColor('#888888')
    )
    teacher_style = ParagraphStyle(
        'CardTeacher', fontName=font_name, fontSize=5.5, leading=7,
        alignment=TA_RIGHT, textColor=colors.HexColor('#555555')
    )

    # ── Student data ──
    student_name = ar(student.name)
    student_code = student.code or ''

    # Group info
    group_info = ''
    group_name = ''
    active_groups = student.student_groups.filter(is_active=True).select_related('group')
    if active_groups.exists():
        sg = active_groups.first()
        group_name = ar(sg.group.name)
        group_info = ar(sg.group.group_type or '')

    # Teacher info
    teacher_name = ''
    try:
        tp = student.teacher.teacher_profile
        teacher_name = ar(
            tp.center_name or tp.full_name or student.teacher.username
        )
    except Exception:
        teacher_name = ar(student.teacher.username)

    # Phone (parent whatsapp if available)
    phone = ''
    primary_link = student.parent_links.filter(
        is_active=True, is_primary_contact=True
    ).select_related('parent').first()
    if primary_link:
        phone = primary_link.parent.whatsapp_number or primary_link.parent.phone or ''
    if not phone:
        phone = student.whatsapp_number or student.phone or ''

    # ── QR code ──
    qr_buf = _make_qr_image(student_code, size_px=100)
    qr_img = RLImage(qr_buf, width=QR_SIZE, height=QR_SIZE)

    # ── Text column ──
    text_col = [
        Paragraph(student_name, name_style),
        Spacer(1, 1.5 * mm),
        Paragraph(group_name, info_style),
        Paragraph(ar(f'النموذج'), info_style),   # matches image label
        Paragraph(teacher_name, teacher_style),
        Spacer(1, 1 * mm),
        Paragraph(student_code, code_style),
    ]
    if phone:
        text_col.append(Paragraph(phone, code_style))

    # ── Card table: [text | QR] ──
    inner = Table(
        [[text_col, qr_img]],
        colWidths=[CARD_W - QR_SIZE - 4 * mm, QR_SIZE],
        rowHeights=[CARD_H - 4 * mm],
    )
    inner.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',   (1, 0), (1, 0),   'CENTER'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1 * mm),
        ('TOPPADDING',   (0, 0), (-1, -1), 1 * mm),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1 * mm),
    ]))

    # ── Outer card wrapper with rounded border ──
    outer = Table(
        [[inner]],
        colWidths=[CARD_W],
        rowHeights=[CARD_H],
    )
    outer.setStyle(TableStyle([
        ('BOX',         (0, 0), (-1, -1), 0.8, colors.HexColor('#CCCCCC')),
        ('ROUNDEDCORNERS', [4]),
        ('BACKGROUND',  (0, 0), (-1, -1), colors.white),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))
    return outer


# ─── Page header/footer callback ──────────────────────────────────────────────

def _make_on_page(teacher_name: str, total_pages_ref: list, font_name: str):
    """Returns an onPage callback for header/footer."""
    def on_page(canvas, doc):
        canvas.saveState()
        page_num = doc.page
        total = total_pages_ref[0] if total_pages_ref else '?'
        today = timezone.now().strftime('%Y/%m/%d')

        # Header: title
        canvas.setFont(font_name, 16)
        canvas.setFillColor(colors.black)
        title = ar('بطاقات الطلاب')
        canvas.drawCentredString(A4[0] / 2, A4[1] - 1.5 * cm, title)

        # Subheader: page info + date
        canvas.setFont(font_name, 9)
        canvas.setFillColor(colors.HexColor('#555555'))
        page_label = ar(f'الصفحة {page_num} من {total} • {today}')
        canvas.drawCentredString(A4[0] / 2, A4[1] - 2.1 * cm, page_label)

        canvas.restoreState()
    return on_page


# ─── Main entry point ─────────────────────────────────────────────────────────

COLS = 3          # cards per row
GAP  = 4 * mm     # horizontal gap between cards
ROW_GAP = 4 * mm  # vertical gap between rows

PAGE_W, PAGE_H = A4
MARGIN_X = (PAGE_W - COLS * CARD_W - (COLS - 1) * GAP) / 2
MARGIN_TOP    = 2.8 * cm   # space for header
MARGIN_BOTTOM = 1.5 * cm


def generate_student_cards_pdf(students) -> bytes:
    """
    Generate a PDF of student ID cards (3 per row, RTL, Arabic).

    :param students: iterable of Student model instances
    :returns: raw PDF bytes
    """
    font_name = _get_arabic_font()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )

    students_list = list(students)
    total_pages_ref = [0]  # will be set after build

    # Build card rows
    cards = [_build_card(s, font_name) for s in students_list]

    # Pad to complete last row
    while len(cards) % COLS != 0:
        cards.append('')   # empty cell

    rows = []
    for i in range(0, len(cards), COLS):
        row = cards[i:i + COLS]
        # RTL: reverse so rightmost card is first in the logical row
        row = list(reversed(row))
        rows.append(row)

    col_widths = [CARD_W] * COLS
    row_heights = [CARD_H + ROW_GAP] * len(rows)

    grid = Table(rows, colWidths=col_widths, rowHeights=row_heights)
    grid.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',   (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING',  (0, 0), (-1, -1), GAP / 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), GAP / 2),
        ('TOPPADDING',   (0, 0), (-1, -1), ROW_GAP / 2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), ROW_GAP / 2),
    ]))

    # Determine teacher name for header
    teacher_name = ''
    if students_list:
        try:
            tp = students_list[0].teacher.teacher_profile
            teacher_name = tp.center_name or tp.full_name or ''
        except Exception:
            pass

    story = [grid]

    # First build to get page count, then rebuild with correct total
    doc.build(
        story,
        onFirstPage=_make_on_page(teacher_name, total_pages_ref, font_name),
        onLaterPages=_make_on_page(teacher_name, total_pages_ref, font_name),
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
