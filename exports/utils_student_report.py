"""
Comprehensive Student Report PDF Generator
Generates a full detailed report per student including:
  - Student info & QR code
  - Attendance summary & history
  - Payments summary
  - Grades summary
  - Behavior assessment summary
"""
from io import BytesIO
from decimal import Decimal
from datetime import date, timedelta

import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether,
)
import arabic_reshaper
from bidi.algorithm import get_display
import os
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q


# ─── Arabic text helper ───────────────────────────────────────────────────────

def _ar(text):
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


# ─── Font ─────────────────────────────────────────────────────────────────────

def _get_font():
    font_name = 'ArabicReport'
    try:
        if font_name in pdfmetrics.getRegisteredFontNames():
            return font_name
        font_path = getattr(settings, 'PDF_ARABIC_FONT_PATH', None)
        if font_path and os.path.exists(str(font_path)):
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
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


# ─── Color Palette ────────────────────────────────────────────────────────────

PRIMARY   = colors.HexColor('#1A73E8')
SECONDARY = colors.HexColor('#34A853')
WARNING   = colors.HexColor('#FBBC04')
DANGER    = colors.HexColor('#EA4335')
DARK      = colors.HexColor('#202124')
GRAY      = colors.HexColor('#9AA0A6')
LIGHT     = colors.HexColor('#F8F9FA')
WHITE     = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


# ─── Style factory ────────────────────────────────────────────────────────────

def _styles(fn):
    return {
        'h1': ParagraphStyle('h1', fontName=fn, fontSize=18, leading=24,
                             alignment=TA_CENTER, textColor=DARK),
        'h2': ParagraphStyle('h2', fontName=fn, fontSize=13, leading=18,
                             alignment=TA_RIGHT, textColor=PRIMARY, spaceBefore=10),
        'h3': ParagraphStyle('h3', fontName=fn, fontSize=10, leading=14,
                             alignment=TA_RIGHT, textColor=DARK, spaceBefore=4),
        'body': ParagraphStyle('body', fontName=fn, fontSize=9, leading=13,
                               alignment=TA_RIGHT, textColor=DARK),
        'small': ParagraphStyle('small', fontName=fn, fontSize=7.5, leading=11,
                                alignment=TA_RIGHT, textColor=GRAY),
        'center': ParagraphStyle('center', fontName=fn, fontSize=9, leading=13,
                                 alignment=TA_CENTER, textColor=DARK),
        'label': ParagraphStyle('label', fontName=fn, fontSize=8, leading=11,
                                alignment=TA_RIGHT, textColor=GRAY),
    }


# ─── QR helper ────────────────────────────────────────────────────────────────

def _qr_img(data, size_cm=2.5):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white').convert('RGB')
    img = img.resize((120, 120), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    s = size_cm * cm
    return RLImage(buf, width=s, height=s)


# ─── Section divider ─────────────────────────────────────────────────────────

def _section(title, fn):
    st = _styles(fn)
    return [
        Spacer(1, 4 * mm),
        Paragraph(_ar(title), st['h2']),
        HRFlowable(width='100%', thickness=0.5, color=PRIMARY, spaceAfter=3 * mm),
    ]


# ─── Info card (2-column key/value table) ────────────────────────────────────

def _info_table(rows, fn, col_widths=None):
    """rows = list of (label, value) tuples"""
    st = _styles(fn)
    col_widths = col_widths or [4 * cm, PAGE_W - 2 * MARGIN - 4 * cm]
    data = [
        [Paragraph(_ar(val), st['body']), Paragraph(_ar(lbl), st['label'])]
        for lbl, val in rows
    ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('ALIGN',        (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME',     (0, 0), (-1, -1), fn),
        ('FONTSIZE',     (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS',(0, 0),(-1,-1), [WHITE, LIGHT]),
        ('GRID',         (0, 0), (-1, -1), 0.3, colors.HexColor('#E8EAED')),
    ]))
    return t


# ─── Rating badge helper ─────────────────────────────────────────────────────

RATING_AR = {
    'excellent': 'ممتاز',
    'good': 'جيد',
    'satisfactory': 'مقبول',
    'needs_improvement': 'يحتاج تحسين',
    'poor': 'ضعيف',
}
RATING_COLOR = {
    'excellent': SECONDARY,
    'good': PRIMARY,
    'satisfactory': WARNING,
    'needs_improvement': DANGER,
    'poor': colors.HexColor('#7F0000'),
}


# ─── Section builders ─────────────────────────────────────────────────────────

def _build_header(student, teacher_profile, fn):
    st = _styles(fn)
    center_name = ''
    teacher_full = ''
    if teacher_profile:
        center_name  = teacher_profile.center_name or ''
        teacher_full = teacher_profile.full_name or teacher_profile.teacher.username
    else:
        teacher_full = student.teacher.username

    today = timezone.now().strftime('%Y/%m/%d')
    qr_img = _qr_img(student.code or str(student.id))

    info_col = [
        Paragraph(_ar('تقرير شامل للطالب'), st['h1']),
        Spacer(1, 2 * mm),
        Paragraph(_ar(center_name), ParagraphStyle('cn', fontName=fn, fontSize=11,
                                                    alignment=TA_CENTER, textColor=PRIMARY)),
        Spacer(1, 1 * mm),
        Paragraph(_ar(f'المدرس: {teacher_full}   |   التاريخ: {today}'),
                  st['small']),
    ]

    t = Table([[info_col, qr_img]], colWidths=[PAGE_W - 2 * MARGIN - 3 * cm, 3 * cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (1, 0), (1, 0), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
    ]))
    return [t, Spacer(1, 4 * mm)]


def _build_student_info(student, fn):
    groups = student.student_groups.filter(is_active=True).select_related('group')
    group_names = '، '.join(g.group.name for g in groups) if groups.exists() else '—'
    sub_ar = {'monthly': 'شهري', 'per_session': 'بالحصة', 'free': 'مجاني'}.get(
        student.subscription_type, student.subscription_type)
    rows = [
        ('الاسم',          student.name),
        ('الكود',          student.code or '—'),
        ('رقم الهاتف',     student.phone or '—'),
        ('واتساب',         student.whatsapp_number or '—'),
        ('المجموعة/ات',    group_names),
        ('نوع الاشتراك',   sub_ar),
        ('السعر الشهري',   f"{student.monthly_price} جنيه" if student.monthly_price else '—'),
        ('تاريخ التسجيل',  str(student.registration_date) if student.registration_date else '—'),
        ('ملاحظات',        student.notes or '—'),
    ]
    return _section('بيانات الطالب', fn) + [_info_table(rows, fn)]


def _build_attendance(student, fn):
    from attendance.models import Attendance
    st = _styles(fn)

    qs = Attendance.objects.filter(student=student).select_related('session')
    total = qs.count()
    present = qs.filter(status='present').count()
    absent  = qs.filter(status='absent').count()
    late    = qs.filter(status='late').count()
    rate    = round(present / total * 100, 1) if total else 0

    summary_rows = [
        ('إجمالي الحصص', str(total)),
        ('حضور',         f"{present} ({rate}%)"),
        ('غياب',         str(absent)),
        ('تأخر',         str(late)),
    ]
    elements = _section('الحضور والغياب', fn) + [_info_table(summary_rows, fn)]

    # Last 15 records table
    recent = qs.order_by('-session__date')[:15]
    if recent:
        STATUS_AR = {'present': 'حضر', 'absent': 'غاب', 'late': 'تأخر', 'excused': 'معذور'}
        STATUS_CLR = {'present': SECONDARY, 'absent': DANGER, 'late': WARNING, 'excused': GRAY}
        headers = [Paragraph(_ar(h), st['label'])
                   for h in ['الحالة', 'ملاحظة', 'التاريخ']]
        rows_data = [headers]
        for rec in recent:
            clr = STATUS_CLR.get(rec.status, DARK)
            rows_data.append([
                Paragraph(_ar(STATUS_AR.get(rec.status, rec.status)),
                           ParagraphStyle('s', fontName=fn, fontSize=8,
                                          textColor=clr, alignment=TA_RIGHT)),
                Paragraph(_ar(rec.notes or '—'), st['small']),
                Paragraph(_ar(str(rec.session.date)), st['small']),
            ])
        col_w = [3 * cm, PAGE_W - 2 * MARGIN - 7 * cm, 4 * cm]
        att_table = Table(rows_data, colWidths=col_w, repeatRows=1)
        att_table.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, 0),   PRIMARY),
            ('TEXTCOLOR',    (0, 0), (-1, 0),   WHITE),
            ('ALIGN',        (0, 0), (-1, -1),  'RIGHT'),
            ('FONTNAME',     (0, 0), (-1, -1),  fn),
            ('FONTSIZE',     (0, 0), (-1, -1),  8),
            ('ROWBACKGROUNDS',(0, 1),(-1, -1),  [WHITE, LIGHT]),
            ('GRID',         (0, 0), (-1, -1),  0.3, colors.HexColor('#E8EAED')),
            ('BOTTOMPADDING',(0, 0), (-1, -1),  3),
            ('TOPPADDING',   (0, 0), (-1, -1),  3),
        ]))
        elements += [Spacer(1, 3 * mm), att_table]

    return elements


def _build_payments(student, fn):
    from payments.models import Payment
    st = _styles(fn)

    qs = Payment.objects.filter(student=student).order_by('-created_at')
    agg = qs.aggregate(
        total_amount=Sum('amount'),
        total_paid=Sum('amount_paid'),
        total_remaining=Sum('remaining_amount'),
        count=Count('id'),
    )

    summary_rows = [
        ('عدد الدفعات',       str(agg['count'] or 0)),
        ('إجمالي المبلغ',     f"{agg['total_amount'] or 0:.2f} جنيه"),
        ('إجمالي المدفوع',    f"{agg['total_paid'] or 0:.2f} جنيه"),
        ('المتبقي',           f"{agg['total_remaining'] or 0:.2f} جنيه"),
    ]
    elements = _section('المدفوعات', fn) + [_info_table(summary_rows, fn)]

    recent = qs[:12]
    if recent:
        TYPE_AR = {
            'monthly': 'شهري', 'session': 'حصة', 'registration': 'تسجيل',
            'material': 'مواد', 'other': 'أخرى',
        }
        STATUS_AR = {
            'paid': 'مدفوع', 'pending': 'معلق', 'partial': 'جزئي',
            'overdue': 'متأخر', 'cancelled': 'ملغي',
        }
        STATUS_CLR = {
            'paid': SECONDARY, 'pending': WARNING, 'partial': PRIMARY,
            'overdue': DANGER, 'cancelled': GRAY,
        }
        headers = [Paragraph(_ar(h), st['label'])
                   for h in ['الحالة', 'المدفوع', 'المبلغ', 'النوع', 'التاريخ']]
        rows_data = [headers]
        for p in recent:
            clr = STATUS_CLR.get(p.status, DARK)
            rows_data.append([
                Paragraph(_ar(STATUS_AR.get(p.status, p.status)),
                           ParagraphStyle('s', fontName=fn, fontSize=8,
                                          textColor=clr, alignment=TA_RIGHT)),
                Paragraph(_ar(f"{p.amount_paid:.0f}"), st['small']),
                Paragraph(_ar(f"{p.amount:.0f}"), st['small']),
                Paragraph(_ar(TYPE_AR.get(p.payment_type, p.payment_type)), st['small']),
                Paragraph(_ar(str(p.payment_date or p.created_at.date())), st['small']),
            ])
        col_w = [2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, PAGE_W - 2*MARGIN - 10*cm]
        pay_table = Table(rows_data, colWidths=col_w, repeatRows=1)
        pay_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  PRIMARY),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
            ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME',      (0, 0), (-1, -1), fn),
            ('FONTSIZE',      (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LIGHT]),
            ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#E8EAED')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ]))
        elements += [Spacer(1, 3 * mm), pay_table]

    return elements


def _build_grades(student, fn):
    from grades.models import Grade
    st = _styles(fn)

    qs = Grade.objects.filter(student=student, is_active=True).select_related('grade_type').order_by('-created_at')
    agg = qs.aggregate(avg=Avg('percentage'), count=Count('id'))

    summary_rows = [
        ('عدد الاختبارات', str(agg['count'] or 0)),
        ('متوسط النسبة',   f"{agg['avg'] or 0:.1f}%"),
    ]
    elements = _section('الدرجات والاختبارات', fn) + [_info_table(summary_rows, fn)]

    recent = qs[:15]
    if recent:
        LETTER_CLR = {'A': SECONDARY, 'B': PRIMARY, 'C': WARNING, 'D': DANGER, 'F': colors.HexColor('#7F0000')}
        headers = [Paragraph(_ar(h), st['label'])
                   for h in ['الدرجة', 'النسبة', 'الدرجة/الكاملة', 'النوع', 'التاريخ']]
        rows_data = [headers]
        for g in recent:
            letter = g.letter_grade or '—'
            clr = LETTER_CLR.get(letter[:1], DARK)
            rows_data.append([
                Paragraph(_ar(letter),
                           ParagraphStyle('s', fontName=fn, fontSize=9,
                                          textColor=clr, alignment=TA_RIGHT)),
                Paragraph(_ar(f"{g.percentage:.1f}%"), st['small']),
                Paragraph(_ar(f"{g.score}/{g.max_score}"), st['small']),
                Paragraph(_ar(g.grade_type.name if g.grade_type else '—'), st['small']),
                Paragraph(_ar(str(g.grade_date if hasattr(g, 'grade_date') else g.created_at.date())), st['small']),
            ])
        col_w = [2*cm, 2.5*cm, 3*cm, PAGE_W - 2*MARGIN - 10.5*cm, 3*cm]
        grade_table = Table(rows_data, colWidths=col_w, repeatRows=1)
        grade_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  PRIMARY),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
            ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME',      (0, 0), (-1, -1), fn),
            ('FONTSIZE',      (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LIGHT]),
            ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#E8EAED')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ]))
        elements += [Spacer(1, 3 * mm), grade_table]

    return elements


def _build_behavior(student, fn):
    st = _styles(fn)

    try:
        from behavior.models import BehaviorRecord
        qs = BehaviorRecord.objects.filter(student=student).select_related('category').order_by('-date')
        agg = qs.aggregate(avg=Avg('score'), count=Count('id'))

        excellent = qs.filter(rating='excellent').count()
        good      = qs.filter(rating='good').count()
        sat       = qs.filter(rating='satisfactory').count()
        neg       = qs.filter(rating__in=['needs_improvement', 'poor']).count()

        summary_rows = [
            ('عدد التقييمات',    str(agg['count'] or 0)),
            ('متوسط الدرجة',     f"{agg['avg'] or 0:.1f} / 5"),
            ('ممتاز',            str(excellent)),
            ('جيد',              str(good)),
            ('مقبول',            str(sat)),
            ('يحتاج تحسين',      str(neg)),
        ]
        elements = _section('التقييم السلوكي', fn) + [_info_table(summary_rows, fn)]

        recent = qs[:12]
        if recent:
            RATING_CLR = {
                'excellent': SECONDARY, 'good': PRIMARY, 'satisfactory': WARNING,
                'needs_improvement': DANGER, 'poor': colors.HexColor('#7F0000'),
            }
            RATING_AR = {
                'excellent': 'ممتاز', 'good': 'جيد', 'satisfactory': 'مقبول',
                'needs_improvement': 'يحتاج تحسين', 'poor': 'ضعيف',
            }
            headers = [Paragraph(_ar(h), st['label'])
                       for h in ['التقييم', 'ملاحظة', 'الجانب', 'التاريخ']]
            rows_data = [headers]
            for b in recent:
                clr = RATING_CLR.get(b.rating, DARK)
                rows_data.append([
                    Paragraph(_ar(RATING_AR.get(b.rating, b.rating)),
                               ParagraphStyle('s', fontName=fn, fontSize=8,
                                              textColor=clr, alignment=TA_RIGHT)),
                    Paragraph(_ar(b.notes or '—'), st['small']),
                    Paragraph(_ar(b.category.name if b.category else 'عام'), st['small']),
                    Paragraph(_ar(str(b.date)), st['small']),
                ])
            col_w = [3*cm, PAGE_W - 2*MARGIN - 10*cm, 4*cm, 3*cm]
            beh_table = Table(rows_data, colWidths=col_w, repeatRows=1)
            beh_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  PRIMARY),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
                ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME',      (0, 0), (-1, -1), fn),
                ('FONTSIZE',      (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LIGHT]),
                ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#E8EAED')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ]))
            elements += [Spacer(1, 3 * mm), beh_table]

        return elements

    except Exception:
        return _section('التقييم السلوكي', fn) + [
            Paragraph(_ar('لا توجد بيانات سلوكية مسجّلة.'), _styles(fn)['small'])
        ]


# ─── Header / Footer callbacks ────────────────────────────────────────────────

def _on_page(student_name, total_pages_ref, fn):
    def callback(canvas, doc):
        canvas.saveState()
        page_num = doc.page
        total = total_pages_ref[0] if total_pages_ref else '?'
        # Top thin line
        canvas.setStrokeColor(PRIMARY)
        canvas.setLineWidth(2)
        canvas.line(MARGIN, PAGE_H - 0.8 * cm, PAGE_W - MARGIN, PAGE_H - 0.8 * cm)
        # Footer
        canvas.setFont(fn, 8)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(
            PAGE_W - MARGIN, 0.7 * cm,
            _ar(f'صفحة {page_num} من {total}  •  {student_name}')
        )
        canvas.restoreState()
    return callback


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_student_report_pdf(student) -> bytes:
    """
    Generate a comprehensive PDF report for a single student.
    :param student: Student model instance
    :returns: raw PDF bytes
    """
    fn = _get_font()
    buffer = BytesIO()

    total_pages_ref = [0]

    # First pass builds the doc to count pages
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 0.5 * cm,
        bottomMargin=MARGIN,
    )

    teacher_profile = None
    try:
        teacher_profile = student.teacher.teacher_profile
    except Exception:
        pass

    story = []
    story += _build_header(student, teacher_profile, fn)
    story += _build_student_info(student, fn)
    story += _build_attendance(student, fn)
    story += _build_payments(student, fn)
    story += _build_grades(student, fn)
    story += _build_behavior(student, fn)

    doc.build(
        story,
        onFirstPage=_on_page(student.name, total_pages_ref, fn),
        onLaterPages=_on_page(student.name, total_pages_ref, fn),
    )

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
