"""
Auto-generate Postman Collection from Django URL patterns.
Run: python generate_postman.py
"""
import os, sys, json, uuid
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')

import django
django.setup()

from django.urls import reverse
from rest_framework.routers import DefaultRouter

BASE = "{{base_url}}"
AUTH_HEADER = {"key": "Authorization", "value": "Bearer {{access_token}}", "type": "text"}

def uid():
    return str(uuid.uuid4())

NO_AUTH = {"type": "noauth"}  # Used for public endpoints

def item(name, method, url_path, body=None, params=None, description="", no_auth=False):
    headers = [{"key": "Content-Type", "value": "application/json", "type": "text"}]
    if not no_auth:
        headers.insert(0, AUTH_HEADER)
    r = {
        "name": name,
        "request": {
            "method": method,
            "header": headers,
            "url": {
                "raw": f"{BASE}/api/{url_path}",
                "host": ["{{base_url}}"],
                "path": ("api/" + url_path).split("/"),
                "query": [{"key": k, "value": v, "description": d, "disabled": True}
                          for k, v, d in (params or [])],
            },
            "description": description,
        },
        "_id": uid(),
    }
    if no_auth:
        r["request"]["auth"] = NO_AUTH
    if body:
        r["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False, indent=2),
                                 "options": {"raw": {"language": "json"}}}
    return r

def folder(name, items):
    return {"name": name, "item": items, "_id": uid()}

# ── Helpers ─────────────────────────────────────────────────────────────────

def crud(prefix, name_prefix, list_params=None, create_body=None, update_body=None, extra_items=None):
    items = [
        item(f"List {name_prefix}", "GET", f"{prefix}/",
             params=list_params or [],
             description=f"GET all {name_prefix}"),
        item(f"Create {name_prefix}", "POST", f"{prefix}/",
             body=create_body or {},
             description=f"POST create {name_prefix}"),
        item(f"Get {name_prefix}", "GET", f"{prefix}/{{{{id}}}}/",
             description=f"GET single {name_prefix}"),
        item(f"Update {name_prefix}", "PUT", f"{prefix}/{{{{id}}}}/",
             body=update_body or create_body or {},
             description=f"PUT update {name_prefix}"),
        item(f"Partial Update {name_prefix}", "PATCH", f"{prefix}/{{{{id}}}}/",
             body={},
             description=f"PATCH partial update"),
        item(f"Delete {name_prefix}", "DELETE", f"{prefix}/{{{{id}}}}/",
             description=f"DELETE {name_prefix}"),
    ]
    if extra_items:
        items += extra_items
    return items

# ════════════════════════════════════════════════════════════════════════════
# FOLDERS
# ════════════════════════════════════════════════════════════════════════════

folders = []

# ── 1. AUTHENTICATION ────────────────────────────────────────────────────────
folders.append(folder("🔐 Authentication", [
    item("Teacher Register", "POST", "auth/teacher-register/", {
        "username": "teacher1", "email": "teacher@example.com",
        "password": "Pass1234!", "first_name": "أحمد", "last_name": "محمد",
        "phone": "01012345678", "center_name": "مركز الأستاذ أحمد",
        "teacher_pin": "1234"
    }, no_auth=True),
    item("Teacher Login (PIN)", "POST", "auth/teacher-login/", {
        "username": "teacher1", "teacher_pin": "1234"
    }, no_auth=True),
    item("Teacher Google Login", "POST", "auth/teacher-google-login/", {
        "id_token": "{{google_id_token}}", "device_info": {}
    }, no_auth=True),
    item("Student Login", "POST", "auth/student-login/", {
        "student_code": "ST-000001"
    }, no_auth=True),
    item("Logout", "POST", "auth/logout/"),
    item("Get Profile", "GET", "auth/profile/"),
    item("Update Profile", "PUT", "auth/profile/update/", {
        "first_name": "أحمد", "center_name": "مركز النجاح"
    }),
    item("Generate Student QR", "POST", "auth/generate-qr/", {
        "student_id": "{{student_id}}"
    }),
    item("Session Status", "GET", "auth/session-status/"),
    item("Extend Session", "POST", "auth/extend-session/"),
]))

# ── 2. STUDENTS ──────────────────────────────────────────────────────────────
student_body = {
    "name": "محمد علي", "phone": "01012345678",
    "whatsapp_number": "01012345678", "email": "student@example.com",
    "date_of_birth": "2010-01-15", "address": "القاهرة",
    "notes": "طالب ملتزم", "subscription_type": "monthly",
    "monthly_price": 300, "per_session_price": 0,
    "student_discount": 0, "discount_type": "percentage",
    "emergency_contact_name": "والد الطالب",
    "emergency_contact_phone": "01098765432",
    "group_id": "{{group_id}}",
    "discount_value": 0, "discount_type": "percentage"
}
student_filters = [
    ("subscription_type", "monthly", "monthly | per_session | free"),
    ("subscription_status", "active", "active | pending | suspended"),
    ("is_active", "true", "true | false"),
    ("search", "محمد", "name, code, phone, email"),
    ("ordering", "-created_at", "name | registration_date | created_at"),
    ("page", "1", "Page number"), ("page_size", "50", "Page size"),
]
folders.append(folder("👨‍🎓 Students", crud(
    "students", "Student",
    list_params=student_filters,
    create_body=student_body,
    extra_items=[
        item("Student Profile (Full)", "GET", "students/{{id}}/profile/"),
        item("Attendance History", "GET", "students/{{id}}/attendance_history/",
             params=[("start_date","2026-01-01","YYYY-MM-DD"),("end_date","2026-02-28","YYYY-MM-DD")]),
        item("Payment History", "GET", "students/{{id}}/payment_history/",
             params=[("status","paid","paid|pending|overdue"),("start_date","",""),("end_date","","")]),
        item("Grades History", "GET", "students/{{id}}/grades_history/",
             params=[("grade_type","","Grade type name"),("start_date","",""),("end_date","","")]),
        item("Update Subscription", "POST", "students/{{id}}/update_subscription/",
             {"subscription_type": "monthly", "subscription_status": "active"}),
        item("Update Remaining Sessions", "POST", "students/{{id}}/update_remaining_sessions/",
             {"sessions_to_add": 5}),
        item("Statistics", "GET", "students/statistics/"),
        # Parents sub-resource
        item("List Parents", "GET", "students/parents/",
             params=[("search","","name, phone, email")]),
        item("Create Parent", "POST", "students/parents/", {
            "name": "والد محمد", "phone": "01098765432",
            "whatsapp_number": "01098765432", "relationship": "father"
        }),
        item("Link Student-Parent", "POST", "students/student-parent-links/", {
            "student": "{{student_id}}", "parent": "{{parent_id}}",
            "is_primary_contact": True, "can_receive_notifications": True,
            "can_view_grades": True, "can_view_attendance": True, "can_view_payments": True
        }),
        item("List Student-Group Links", "GET", "students/student-groups/"),
        item("Enroll Student in Group", "POST", "students/student-groups/", {
            "student": "{{student_id}}", "group": "{{group_id}}",
            "custom_monthly_price": None, "custom_session_price": None
        }),
        item("Remove Student from Group", "DELETE", "students/student-groups/{{id}}/"),
    ]
)))

# ── 3. GROUPS ────────────────────────────────────────────────────────────────
group_body = {
    "name": "الصف الثاني إعدادي - أ", "group_type": "center",
    "monthly_price": 350, "session_price": 0,
    "sessions_per_month": 8, "max_students": 20,
    "group_discount": 0, "notes": "مجموعة الصباح",
    "subject": "رياضيات", "level": "إعدادي"
}
group_filters = [
    ("group_type","center","center|premium_center|private|online|special"),
    ("is_active","true","true|false"),
    ("search","","name, subject"),
    ("ordering","-created_at","name|created_at"),
]
folders.append(folder("👥 Groups", crud(
    "groups", "Group",
    list_params=group_filters,
    create_body=group_body,
    extra_items=[
        item("Group Statistics", "GET", "groups/{{id}}/statistics/"),
        item("Group Students", "GET", "groups/{{id}}/students/"),
        item("Add Schedule", "POST", "groups/schedules/", {
            "group": "{{group_id}}", "day_of_week": 0,
            "start_time": "16:00", "end_time": "17:30", "room": "قاعة 1"
        }),
        item("List Schedules", "GET", "groups/schedules/",
             params=[("group","{{group_id}}","Filter by group")]),
        item("Add Announcement", "POST", "groups/announcements/", {
            "group": "{{group_id}}", "title": "إعلان هام",
            "content": "سيتم إلغاء حصة الخميس", "is_pinned": False
        }),
        item("List Materials", "GET", "groups/materials/",
             params=[("group","{{group_id}}","Filter by group")]),
    ]
)))

# ── 4. SESSIONS ──────────────────────────────────────────────────────────────
session_body = {
    "group": "{{group_id}}", "title": "الدرس الأول - المعادلات",
    "description": "شرح المعادلات التربيعية",
    "date": "2026-02-25", "start_time": "16:00", "end_time": "17:30",
    "repeat_type": "weekly", "repeat_until": "2026-05-30",
    "status": "scheduled", "lesson_content": "المعادلات التربيعية",
    "homework_assigned": "حل تمارين الكتاب ص45"
}
session_filters = [
    ("group","{{group_id}}","Filter by group"),
    ("status","scheduled","scheduled|in_progress|completed|cancelled|postponed"),
    ("date","2026-02-25","Exact date YYYY-MM-DD"),
    ("date__gte","2026-02-01","Date from"),
    ("date__lte","2026-02-28","Date to"),
    ("search","","title, description"),
    ("ordering","date","date|-date"),
]
folders.append(folder("📅 Sessions", crud(
    "sessions", "Session",
    list_params=session_filters,
    create_body=session_body,
    extra_items=[
        item("Today Sessions", "GET", "sessions/today/"),
        item("Upcoming Sessions", "GET", "sessions/upcoming/",
             params=[("days","7","Number of days ahead")]),
        item("Session Statistics", "GET", "sessions/statistics/"),
        item("Mark Complete", "POST", "sessions/{{id}}/mark_complete/", {
            "notes": "تم الشرح بنجاح"
        }),
        item("Cancel Session", "POST", "sessions/{{id}}/cancel/", {
            "reason": "إجازة رسمية"
        }),
        item("Add Session Note", "POST", "sessions/session-notes/", {
            "session": "{{session_id}}", "note": "الطلاب فهموا الدرس",
            "note_type": "general", "is_private": False
        }),
        item("Add Reminder", "POST", "sessions/session-reminders/", {
            "session": "{{session_id}}", "reminder_type": "whatsapp",
            "minutes_before": 60, "message": "تذكير: موعد الحصة غداً"
        }),
    ]
)))

# ── 5. ATTENDANCE ────────────────────────────────────────────────────────────
attendance_body = {
    "student": "{{student_id}}", "session": "{{session_id}}",
    "status": "present", "notes": "", "marked_by": "manual"
}
attendance_filters = [
    ("student","{{student_id}}","Filter by student"),
    ("session","{{session_id}}","Filter by session"),
    ("status","present","present|absent|late|excused"),
    ("date","2026-02-25","Date YYYY-MM-DD"),
    ("date__gte","2026-02-01",""),("date__lte","2026-02-28",""),
    ("search","","student name or code"),
    ("group_id","{{group_id}}","Filter by group"),
]
folders.append(folder("✅ Attendance", crud(
    "attendance", "Attendance",
    list_params=attendance_filters,
    create_body=attendance_body,
    extra_items=[
        item("Bulk Mark Attendance", "POST", "attendance/bulk_mark/", {
            "session_id": "{{session_id}}",
            "attendance": [
                {"student_id": "{{student_id}}", "status": "present", "notes": ""},
                {"student_id": "{{student_id_2}}", "status": "absent", "notes": "مريض"}
            ]
        }),
        item("Session Attendance", "GET", "attendance/session_attendance/",
             params=[("session_id","{{session_id}}","Required")]),
        item("Scan QR Attendance", "POST", "attendance/scan_qr/", {
            "qr_token": "{{qr_token}}", "session_id": "{{session_id}}"
        }),
        item("Attendance Summary (Student)", "GET", "attendance/summaries/",
             params=[("student","{{student_id}}",""),("month","2","1-12"),("year","2026","")]),
        item("Attendance Alerts", "GET", "attendance/alerts/",
             params=[("is_resolved","false","true|false"),("alert_type","consecutive_absence","")]),
    ]
)))

# ── 6. PAYMENTS ──────────────────────────────────────────────────────────────
payment_body = {
    "student": "{{student_id}}", "payment_type": "monthly",
    "amount": 300, "amount_paid": 300,
    "payment_method": "cash", "payment_date": "2026-02-23",
    "period_start": "2026-02-01", "period_end": "2026-02-28",
    "notes": "دفع شهر فبراير", "discount_amount": 0,
    "discount_reason": "", "session_count": 0
}
payment_filters = [
    ("student","{{student_id}}",""),
    ("payment_type","monthly","monthly|session|registration|material|other"),
    ("status","paid","paid|pending|partial|overdue|cancelled|refunded"),
    ("payment_method","cash","cash|bank_transfer|mobile_payment|check|other"),
    ("payment_date__gte","2026-02-01",""),("payment_date__lte","2026-02-28",""),
    ("search","","student name or code"),
    ("ordering","-created_at",""),
]
folders.append(folder("💰 Payments", crud(
    "payments", "Payment",
    list_params=payment_filters,
    create_body=payment_body,
    extra_items=[
        item("Payment Statistics", "GET", "payments/statistics/"),
        item("Overdue Payments", "GET", "payments/overdue/"),
        item("Monthly Summary", "GET", "payments/monthly_summary/",
             params=[("month","2","1-12"),("year","2026","")]),
        item("Mark as Paid", "POST", "payments/{{id}}/mark_paid/", {
            "amount_paid": 300, "payment_method": "cash",
            "payment_date": "2026-02-23"
        }),
        item("Payment Reminders", "GET", "payments/payment-reminders/"),
        item("Add Payment Reminder", "POST", "payments/payment-reminders/", {
            "payment": "{{payment_id}}", "reminder_type": "whatsapp",
            "scheduled_at": "2026-02-25T10:00:00Z"
        }),
    ]
)))

# ── 7. RECEIPTS ──────────────────────────────────────────────────────────────
receipt_body = {
    "payment": "{{payment_id}}", "receipt_type": "payment",
    "title": "إيصال دفع - محمد علي", "description": "دفع شهر فبراير 2026",
    "amount": 300, "notes": ""
}
receipt_filters = [
    ("payment","{{payment_id}}",""),
    ("status","generated","pending|generated|sent|failed"),
    ("receipt_type","payment","payment|monthly|registration|refund"),
    ("search","","receipt number or student name"),
    ("ordering","-created_at",""),
]
folders.append(folder("🧾 Receipts", crud(
    "receipts", "Receipt",
    list_params=receipt_filters,
    create_body=receipt_body,
    extra_items=[
        item("Generate PDF", "POST", "receipts/{{id}}/generate_pdf/"),
        item("Send Receipt", "POST", "receipts/{{id}}/send/", {
            "channel": "whatsapp"
        }),
        item("Bulk Generate", "POST", "receipts/bulk_generate/", {
            "receipt_ids": ["{{receipt_id}}"]
        }),
        item("Receipt Templates", "GET", "receipts/templates/"),
        item("Create Template", "POST", "receipts/templates/", {
            "name": "قالب افتراضي", "header_text": "مركز النجاح",
            "footer_text": "شكراً لثقتكم", "show_logo": True
        }),
    ]
)))

# ── 8. GRADES ────────────────────────────────────────────────────────────────
grade_body = {
    "student": "{{student_id}}", "grade_type": "{{grade_type_id}}",
    "session": None, "score": 85, "max_score": 100,
    "notes": "أداء جيد", "grade_date": "2026-02-23"
}
grade_filters = [
    ("student","{{student_id}}",""),
    ("grade_type","{{grade_type_id}}",""),
    ("session","{{session_id}}",""),
    ("grade_date__gte","2026-02-01",""),("grade_date__lte","2026-02-28",""),
    ("search","","student name"),
    ("ordering","-created_at",""),
]
folders.append(folder("📊 Grades", crud(
    "grades", "Grade",
    list_params=grade_filters,
    create_body=grade_body,
    extra_items=[
        item("Grade Statistics", "GET", "grades/statistics/"),
        item("Student Average", "GET", "grades/student_average/",
             params=[("student_id","{{student_id}}","Required")]),
        item("Grade Alert", "GET", "grades/alerts/",
             params=[("is_resolved","false","true|false"),("student","{{student_id}}","")]),
        item("Grade Types", "GET", "grades/grade-types/"),
        item("Create Grade Type", "POST", "grades/grade-types/", {
            "name": "اختبار شهري", "name_en": "Monthly Test",
            "max_score": 100, "weight": 1.0, "is_active": True,
            "description": ""
        }),
        item("Grade Summary", "GET", "grades/summaries/",
             params=[("student","{{student_id}}",""),("month","2",""),("year","2026","")]),
    ]
)))

# ── 9. NOTIFICATIONS ─────────────────────────────────────────────────────────
notif_body = {
    "recipient_type": "student", "recipient_id": "{{student_id}}",
    "recipient_name": "محمد علي", "recipient_phone": "01012345678",
    "title": "تذكير بموعد الحصة", "message": "موعد حصتك غداً الساعة 4 عصراً",
    "notification_type": "session_reminder", "channel": "whatsapp",
    "scheduled_at": None
}
notif_filters = [
    ("status","pending","pending|sent|failed|cancelled"),
    ("channel","whatsapp","whatsapp|email|push|sms"),
    ("notification_type","payment_reminder","payment_reminder|session_reminder|grade_notification|alert|general"),
    ("recipient_type","student","student|parent|teacher"),
    ("search","","title, message, recipient_name"),
    ("ordering","-created_at",""),
]
folders.append(folder("🔔 Notifications", crud(
    "notifications", "Notification",
    list_params=notif_filters,
    create_body=notif_body,
    extra_items=[
        item("Send Notification", "POST", "notifications/{{id}}/send/"),
        item("Bulk Send", "POST", "notifications/bulk_send/", {
            "student_ids": ["{{student_id}}"],
            "title": "إعلان هام", "message": "سيتم إلغاء حصة الخميس",
            "channel": "whatsapp", "notification_type": "general"
        }),
        item("Pending Notifications", "GET", "notifications/pending/"),
        item("Notification Templates", "GET", "notifications/templates/"),
        item("Create Template", "POST", "notifications/templates/", {
            "name": "تذكير الدفع", "notification_type": "payment_reminder",
            "channel": "whatsapp",
            "title_template": "تذكير بدفع {month}",
            "message_template": "عزيزي {student_name}, رجاء سداد اشتراك {month}"
        }),
        item("Notification Stats", "GET", "notifications/statistics/"),
    ]
)))

# ── 10. BEHAVIOR ─────────────────────────────────────────────────────────────
behavior_body = {
    "student": "{{student_id}}", "category": "{{category_id}}",
    "session": None, "rating": "good",
    "notes": "الطالب ملتزم ومنتبه", "date": "2026-02-23"
}
behavior_filters = [
    ("student","{{student_id}}",""),
    ("category","{{category_id}}",""),
    ("rating","good","excellent|good|satisfactory|needs_improvement|poor"),
    ("session","{{session_id}}",""),
    ("parent_notified","false","true|false"),
    ("start_date","2026-02-01","YYYY-MM-DD"),("end_date","2026-02-28","YYYY-MM-DD"),
    ("group_id","{{group_id}}","Filter all students in group"),
    ("search","","student name or code"),
]
folders.append(folder("🧠 Behavior Assessment", [
    *crud("behavior/records","Behavior Record",
          list_params=behavior_filters, create_body=behavior_body,
          extra_items=[
              item("Notify Parent", "POST", "behavior/records/{{id}}/notify_parent/"),
              item("Bulk Create Records", "POST", "behavior/records/bulk_create/", {
                  "student_ids": ["{{student_id}}", "{{student_id_2}}"],
                  "category": "{{category_id}}", "session": None,
                  "rating": "good", "notes": "أداء جيد اليوم",
                  "date": "2026-02-23"
              }),
              item("Statistics", "GET", "behavior/records/statistics/",
                   params=[("student_id","{{student_id}}",""),
                           ("group_id","{{group_id}}",""),
                           ("start_date","",""),("end_date","","")]),
          ]),
    item("List Categories", "GET", "behavior/categories/"),
    item("Create Category", "POST", "behavior/categories/", {
        "name": "الالتزام بالواجب", "name_en": "Homework",
        "icon": "book", "color": "#4A90D9", "notify_on_negative": True
    }),
    item("Get Category", "GET", "behavior/categories/{{id}}/"),
    item("Update Category", "PUT", "behavior/categories/{{id}}/", {
        "name": "المشاركة", "notify_on_negative": False
    }),
    item("Delete Category", "DELETE", "behavior/categories/{{id}}/"),
    item("List Summaries", "GET", "behavior/summaries/",
         params=[("student","{{student_id}}",""),("summary_type","monthly","monthly|weekly")]),
    item("Generate Summary", "POST", "behavior/summaries/generate/", {
        "student_id": "{{student_id}}", "summary_type": "monthly",
        "period_start": "2026-02-01", "period_end": "2026-02-28"
    }),
]))

# ── 11. EXPORTS / PDF ────────────────────────────────────────────────────────
folders.append(folder("📄 Exports & PDFs", [
    item("Export Students CSV", "POST", "exports/exports/students/", {
        "format": "csv", "filters": {"subscription_type": "monthly"},
        "fields": ["name","phone","code","subscription_type"]
    }),
    item("Export Payments CSV", "POST", "exports/exports/payments/", {
        "format": "csv", "filters": {"start_date": "2026-02-01", "end_date": "2026-02-28"}
    }),
    item("Export Attendance CSV", "POST", "exports/exports/attendance/", {
        "format": "csv", "filters": {"start_date": "2026-02-01", "status": "absent"}
    }),
    item("Export Grades CSV", "POST", "exports/exports/grades/", {"format": "csv", "filters": {}}),
    item("Export Groups CSV", "POST", "exports/exports/groups/", {"format": "csv", "filters": {}}),
    item("📇 Generate Student Cards PDF", "POST", "exports/exports/student_cards/", {
        "student_ids": ["{{student_id}}", "{{student_id_2}}"]
    }),
    item("📇 Generate Cards by Group", "POST", "exports/exports/student_cards/", {
        "group_id": "{{group_id}}"
    }),
    item("📋 Comprehensive Student Report PDF", "POST", "exports/exports/student_report/", {
        "student_code": "ST-000001"
    }),
    item("📋 Student Report by ID", "POST", "exports/exports/student_report/", {
        "student_id": "{{student_id}}"
    }),
    item("Download Export", "GET", "exports/exports/{{id}}/download/"),
    item("Export Status", "GET", "exports/exports/{{id}}/status_/"),
    item("List Exports", "GET", "exports/exports/"),
]))

# ── 12. SMART INSIGHTS ───────────────────────────────────────────────────────
folders.append(folder("💡 Smart Insights", [
    item("List Insights", "GET", "insights/insights/",
         params=[("status","active","active|dismissed|resolved"),
                 ("insight_type","",""),("search","","")]),
    item("Create Insight", "POST", "insights/insights/", {
        "title": "طالب في خطر التسرب", "description": "غاب أكثر من 5 مرات هذا الشهر",
        "insight_type": "attendance", "priority": "high",
        "student": "{{student_id}}"
    }),
    item("Dismiss Insight", "POST", "insights/insights/{{id}}/dismiss/"),
    item("List Alerts", "GET", "insights/alerts/",
         params=[("is_resolved","false",""),("severity","high","low|medium|high|critical")]),
    item("Resolve Alert", "POST", "insights/alerts/{{id}}/resolve/"),
    item("List Suggestions", "GET", "insights/suggestions/"),
    item("Apply Suggestion", "POST", "insights/suggestions/{{id}}/apply/"),
    item("Analytics Snapshot", "GET", "insights/snapshots/",
         params=[("snapshot_type","monthly","daily|weekly|monthly"),
                 ("date__gte","2026-01-01","")]),
    item("Generate Snapshot", "POST", "insights/snapshots/generate/", {
        "snapshot_type": "monthly", "date": "2026-02-23"
    }),
    item("Dashboard Widgets", "GET", "insights/widgets/"),
]))

# ── 13. REPORTS ──────────────────────────────────────────────────────────────
folders.append(folder("📈 Reports", [
    item("List Reports", "GET", "reports/reports/",
         params=[("report_type","student_report","student_report|monthly_financial|attendance_report|grade_report"),
                 ("status","completed","pending|processing|completed|failed"),
                 ("ordering","-created_at","")]),
    item("Generate Report", "POST", "reports/reports/", {
        "report_type": "monthly_financial", "format": "pdf",
        "period_start": "2026-02-01", "period_end": "2026-02-28",
        "title": "التقرير المالي - فبراير 2026",
        "filters": {"group_id": None}
    }),
    item("Download Report", "GET", "reports/reports/{{id}}/download/"),
    item("Report Templates", "GET", "reports/templates/"),
]))

# ── 14. SETTINGS ─────────────────────────────────────────────────────────────
folders.append(folder("⚙️ Settings", [
    item("Get App Settings", "GET", "settings/app-settings/"),
    item("Update Settings", "PUT", "settings/app-settings/1/", {
        "center_name": "مركز النجاح", "language": "ar", "theme": "light",
        "currency": "EGP", "consecutive_absences_alert": 3,
        "overdue_payment_days": 7, "low_grade_threshold": 50,
        "whatsapp_notifications_enabled": True,
        "payment_reminder_days_before": 3
    }),
    item("Danger Zone Actions Log", "GET", "settings/danger-zone/"),
    item("Reset Data", "POST", "settings/danger-zone/", {
        "action_type": "delete_students",
        "confirmation": "DELETE", "teacher_pin": "1234"
    }),
]))

# ── 15. SUBSCRIPTIONS ────────────────────────────────────────────────────────
folders.append(folder("💳 Teacher Subscriptions", [
    item("My Subscription", "GET", "subscriptions/plans/my_plan/"),
    item("List Plans", "GET", "subscriptions/plans/"),
    item("Upgrade Plan", "POST", "subscriptions/plans/upgrade/", {
        "plan": "professional", "payment_method": "cash"
    }),
]))

# ── 16. TEACHERS ─────────────────────────────────────────────────────────────
folders.append(folder("👨‍🏫 Teacher Profile", [
    item("Get Teacher Profile", "GET", "teachers/profile/"),
    item("Update Teacher Profile", "PUT", "teachers/profile/update/", {
        "center_name": "مركز النجاح", "full_name": "أحمد محمد",
        "phone": "01012345678", "address": "القاهرة",
        "bio": "مدرس رياضيات خبرة 10 سنوات",
        "max_students": 100, "max_groups": 20
    }),
    item("Teacher Statistics", "GET", "teachers/profile/statistics/"),
    item("Notification Settings", "GET", "teachers/notification-settings/"),
    item("Update Notification Settings", "PUT", "teachers/notification-settings/{{id}}/", {
        "payment_reminders_enabled": True,
        "session_reminders_enabled": True,
        "whatsapp_enabled": True, "email_enabled": False,
        "reminder_time_before_session": 60
    }),
]))

# ── 17. RULES ENGINE ─────────────────────────────────────────────────────────
folders.append(folder("⚡ Rules Engine", [
    item("List Rules", "GET", "rules/rules/",
         params=[("is_active","true",""),("rule_type","","")]),
    item("Create Rule", "POST", "rules/rules/", {
        "name": "تنبيه الغياب المتكرر", "rule_type": "attendance",
        "condition": {"consecutive_absences": 3}, "is_active": True,
        "action": {"notify_parent": True, "create_alert": True}
    }),
    item("Toggle Rule", "POST", "rules/rules/{{id}}/toggle/"),
    item("Run Rules Now", "POST", "rules/run/"),
]))

# ── 18. AUDIT LOGS ───────────────────────────────────────────────────────────
folders.append(folder("📋 Audit Logs", [
    item("List Logs", "GET", "audit/logs/",
         params=[("action","","create|update|delete|login|logout"),
                 ("model","","Student|Payment|Group..."),
                 ("start_date","",""),("end_date","",""),
                 ("search","",""),("ordering","-created_at","")]),
]))

# ── 19. SYNC ─────────────────────────────────────────────────────────────────
folders.append(folder("🔄 Sync", [
    item("Sync Status", "GET", "sync/status/"),
    item("Push Sync", "POST", "sync/push/", {
        "device_id": "{{device_id}}",
        "last_sync": "2026-02-23T00:00:00Z",
        "data": {}
    }),
    item("Pull Sync", "POST", "sync/pull/", {
        "device_id": "{{device_id}}",
        "last_sync": "2026-02-23T00:00:00Z"
    }),
]))

# ── 20. ADMIN (Updated) ──────────────────────────────────────────────────────
plan_body = {
    "name": "Professional",
    "name_ar": "الخطة الاحترافية",
    "description": "للمدرسين المحترفين",
    "price": 99.00,
    "billing_cycle": "monthly",
    "duration_days": 30,
    "max_students": 100,
    "max_groups": 20,
    "storage_gb": 10,
    "is_popular": True,
    "features": ["إشعارات واتساب", "تصدير PDF", "تقارير متقدمة"]
}
folders.append(folder("🛡️ Admin", [

    # ── Admin Auth ──────────────────────────────────────────────────────────
    item("Admin Login", "POST", "admin/login/",
         body={"username": "admin", "password": "Admin1234!"},
         description="No Authorization header required. Returns JWT + platform stats.",
         no_auth=True),

    # ── Teacher management ──────────────────────────────────────────────────
    item("List All Teachers", "GET", "admin/teachers/",
         params=[("subscription_plan","","trial|basic|professional|unlimited"),
                 ("is_active","true",""),("search","","username, email")]),
    item("Teacher Details", "GET", "admin/teachers/{{id}}/"),
    item("Toggle Teacher Active", "POST", "admin/teachers/{{id}}/toggle_active/"),
    item("Platform Stats", "GET", "admin/teachers/statistics/"),

    # ── Subscription Plans CRUD ─────────────────────────────────────────────
    item("List Plans", "GET", "admin/plans/",
         params=[("search","","name, description"),("ordering","price","price|duration_days|created_at")]),
    item("Create Plan", "POST", "admin/plans/", body=plan_body),
    item("Get Plan", "GET", "admin/plans/{{plan_id}}/"),
    item("Update Plan", "PUT", "admin/plans/{{plan_id}}/", body=plan_body),
    item("Partial Update Plan", "PATCH", "admin/plans/{{plan_id}}/",
         body={"price": 79.00, "is_popular": False}),
    item("Delete Plan", "DELETE", "admin/plans/{{plan_id}}/",
         description="Only succeeds if plan has 0 active subscribers."),
    item("Toggle Plan Active", "POST", "admin/plans/{{plan_id}}/toggle_active/",
         description="Activates plan if inactive, deactivates if active."),

    # ── Teacher Subscriptions management ────────────────────────────────────
    item("List Teacher Subscriptions", "GET", "admin/teacher-subscriptions/",
         params=[("status","active","active|expired|cancelled|trial"),
                 ("plan","{{plan_id}}","Filter by plan"),
                 ("search","","username, email, plan name"),
                 ("ordering","-created_at","")]),
    item("Assign Plan to Teacher", "POST", "admin/teacher-subscriptions/", body={
        "teacher": "{{teacher_user_id}}",
        "plan": "{{plan_id}}",
        "status": "active",
        "start_date": "2026-02-23",
        "end_date": None,
        "auto_renew": True
    }, description="end_date auto-calculated from plan.duration_days if not provided."),
    item("Get Teacher Subscription", "GET", "admin/teacher-subscriptions/{{sub_id}}/"),
    item("Update Subscription", "PUT", "admin/teacher-subscriptions/{{sub_id}}/", body={
        "teacher": "{{teacher_user_id}}", "plan": "{{plan_id}}",
        "status": "active", "start_date": "2026-02-23", "end_date": "2026-03-23"
    }),
    item("Extend Subscription", "POST", "admin/teacher-subscriptions/{{sub_id}}/extend/",
         body={"days": 30},
         description="Adds N days from today (or from current end_date if future)."),
    item("Revoke Subscription", "POST", "admin/teacher-subscriptions/{{sub_id}}/revoke/",
         description="Cancels subscription immediately."),
    item("Expiring Soon", "GET", "admin/teacher-subscriptions/expiring_soon/",
         params=[("days","7","Subscriptions expiring within N days")]),
]))

# ── 21. WEEKLY SCHEDULE (new) ─────────────────────────────────────────────────
folders.append(folder("📆 Weekly Schedule", [
    item("Current Week Schedule", "GET", "sessions/sessions/weekly_schedule/",
         description="Returns 7-day calendar view with sessions grouped by Arabic day name."),
    item("Specific Week Schedule", "GET", "sessions/sessions/weekly_schedule/",
         params=[("week_start","2026-02-23","YYYY-MM-DD — auto-snaps to Monday"),
                 ("group_id","{{group_id}}","Optional: filter to one group")]),
    item("Group Week Schedule", "GET", "sessions/sessions/weekly_schedule/",
         params=[("group_id","{{group_id}}","Show only this group's schedule"),
                 ("week_start","","YYYY-MM-DD")]),
]))

# ════════════════════════════════════════════════════════════════════════════
# BUILD COLLECTION
# ════════════════════════════════════════════════════════════════════════════

collection = {
    "info": {
        "name": "Smart Teacher Assistant - Complete API",
        "description": (
            "Comprehensive Postman collection for all Smart Teacher Assistant APIs.\n"
            "Base URL variable: base_url = http://127.0.0.1:8000\n"
            "Auth: set access_token after login.\n\n"
            "v2.0 — includes: Admin Login, Subscription Plans, "
            "Teacher Subscriptions, Behavior Assessment, Student Cards PDF, "
            "Comprehensive Student Report PDF, Weekly Schedule."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        "_postman_id": uid(),
        "version": "2.0.0"
    },
    "variable": [
        {"key": "base_url",         "value": "http://127.0.0.1:8000", "type": "string"},
        {"key": "access_token",     "value": "", "type": "string"},
        {"key": "student_id",       "value": "", "type": "string"},
        {"key": "student_id_2",     "value": "", "type": "string"},
        {"key": "group_id",         "value": "", "type": "string"},
        {"key": "session_id",       "value": "", "type": "string"},
        {"key": "payment_id",       "value": "", "type": "string"},
        {"key": "receipt_id",       "value": "", "type": "string"},
        {"key": "parent_id",        "value": "", "type": "string"},
        {"key": "grade_type_id",    "value": "", "type": "string"},
        {"key": "category_id",      "value": "", "type": "string"},
        {"key": "plan_id",          "value": "", "type": "string"},
        {"key": "sub_id",           "value": "", "type": "string"},
        {"key": "teacher_user_id",  "value": "", "type": "string"},
        {"key": "device_id",        "value": "flutter-app-001", "type": "string"},
    ],
    "auth": {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]
    },
    "item": folders
}

output_path = os.path.join(os.path.dirname(__file__), "Smart_Teacher_Assistant.postman_collection.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(collection, f, ensure_ascii=False, indent=2)

print(f"[OK] Postman collection generated: {output_path}")
print(f"     Total folders: {len(folders)}")
total_requests = sum(len(f.get('item', [])) for f in folders)
print(f"     Total requests: {total_requests}")
