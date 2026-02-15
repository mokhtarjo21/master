# Smart Teacher Assistant - API Contract

## Table of Contents
- [Authentication](#authentication)
- [Base URLs & Headers](#base-urls--headers)
- [Error Handling](#error-handling)
- [Pagination](#pagination)
- [User Management](#user-management)
- [Teachers](#teachers)
- [Students](#students)
- [Parents](#parents)
- [Groups](#groups)
- [Sessions](#sessions)
- [Attendance](#attendance)
- [Payments](#payments)
- [Receipts](#receipts)
- [Grades](#grades)
- [Reports](#reports)
- [Notifications](#notifications)
- [Smart Insights](#smart-insights)
- [Rules Engine](#rules-engine)
- [Settings](#settings)
- [Subscriptions](#subscriptions)
- [Exports](#exports)
- [Sync](#sync)
- [Audit Logs](#audit-logs)

---

## Authentication

### Teacher Login (PIN-based)
```http
POST /api/auth/teacher-login/
Content-Type: application/json

{
  "pin": "1234",
  "device_info": {
    "device_type": "mobile",
    "device_id": "abc123",
    "app_version": "1.0.0"
  }
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid",
    "username": "teacher_username",
    "center_name": "My Learning Center",
    "language": "ar"
  },
  "session_token": "session_uuid"
}
```

### Student/Parent Login
```http
POST /api/auth/student-login/
Content-Type: application/json

# Option 1: Student Code
{
  "student_code": "ST-1234567"
}

# Option 2: Access Token
{
  "access_token": "secure_token_here"
}

# Option 3: QR Token
{
  "qr_token": "qr_token_here"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid",
    "username": "ST-1234567",
    "user_type": "student",
    "language": "ar"
  }
}
```

### Generate QR Code for Student Access
```http
POST /api/auth/generate-qr/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "student_id": "uuid"
}
```

**Response:**
```json
{
  "qr_token": "secure_qr_token",
  "expires_at": "2024-01-15T10:30:00Z",
  "qr_url": "/api/auth/student-login/?qr_token=secure_qr_token"
}
```

---

## Base URLs & Headers

**Base URL:** `https://api.smartteacher.com/api/`

**Required Headers:**
```http
Authorization: Bearer {jwt_token}
Content-Type: application/json
Accept-Language: ar  # or 'en'
```

---

## Error Handling

**Standard Error Response:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "field_name": ["Field-specific error message"]
  }
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

---

## Pagination

**Request:**
```http
GET /api/endpoint/?page=1&page_size=50
```

**Response:**
```json
{
  "count": 150,
  "next": "https://api.smartteacher.com/api/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## User Management

### Get Current User Profile
```http
GET /api/auth/profile/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "username": "teacher_username",
  "email": "teacher@example.com",
  "user_type": "teacher",
  "language": "ar",
  "center_name": "My Learning Center",
  "last_activity": "2024-01-15T10:30:00Z"
}
```

### Update Profile
```http
PUT /api/auth/profile/
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "language": "en",
  "center_name": "Updated Center Name"
}
```

---

## Teachers

### Get Teacher Dashboard
```http
GET /api/teachers/profile/dashboard/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "total_students": 45,
  "active_students": 42,
  "total_groups": 8,
  "active_groups": 7,
  "today_sessions": 3,
  "pending_payments": "1250.00",
  "overdue_payments": "300.00",
  "monthly_revenue": "15000.00",
  "attendance_rate": 87.5,
  "recent_alerts": [
    {
      "id": "uuid",
      "title": "Low Attendance Alert",
      "message": "Student Ahmed has missed 3 consecutive sessions",
      "severity": "high",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "upcoming_sessions": [
    {
      "id": "uuid",
      "group_name": "Math Grade 10",
      "date": "2024-01-16",
      "start_time": "14:00:00",
      "end_time": "15:30:00"
    }
  ]
}
```

### Get Teacher Statistics
```http
GET /api/teachers/profile/stats/?type=daily&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {teacher_token}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "date": "2024-01-15",
    "stat_type": "daily",
    "total_students": 45,
    "active_students": 42,
    "total_revenue": "500.00",
    "attendance_rate": 85.5,
    "revenue_growth": 12.5
  }
]
```

---

## Students

### List Students
```http
GET /api/students/students/?subscription_type=monthly&search=ahmed
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 25,
  "results": [
    {
      "id": "uuid",
      "name": "Ahmed Ali",
      "code": "ST-1234567",
      "phone": "+966501234567",
      "subscription_type": "monthly",
      "subscription_status": "active",
      "remaining_sessions": 8,
      "remaining_amount": "150.00",
      "groups_count": 2,
      "last_attendance": {
        "date": "2024-01-15",
        "status": "present"
      },
      "payment_status": "paid",
      "is_active": true
    }
  ]
}
```

### Create Student
```http
POST /api/students/students/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "name": "Ahmed Ali",
  "phone": "+966501234567",
  "whatsapp_number": "+966501234567",
  "email": "ahmed@example.com",
  "date_of_birth": "2005-03-15",
  "address": "Riyadh, Saudi Arabia",
  "subscription_type": "monthly",
  "monthly_price": "200.00",
  "student_discount": "10.00",
  "emergency_contact_name": "Father Name",
  "emergency_contact_phone": "+966501234568"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Ahmed Ali",
  "code": "ST-1234567",
  "phone": "+966501234567",
  "subscription_type": "monthly",
  "subscription_status": "active",
  "monthly_price": "200.00",
  "student_discount": "10.00",
  "remaining_amount": "0.00",
  "is_active": true,
  "registration_date": "2024-01-15",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Student Profile
```http
GET /api/students/students/{student_id}/profile/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Ahmed Ali",
  "code": "ST-1234567",
  "phone": "+966501234567",
  "subscription_type": "monthly",
  "subscription_status": "active",
  "monthly_price": "200.00",
  "remaining_amount": "150.00",
  "attendance_summary": {
    "monthly_total": 12,
    "monthly_present": 10,
    "monthly_absent": 2,
    "monthly_rate": 83.33,
    "overall_rate": 87.5
  },
  "payment_summary": {
    "total_paid": "1800.00",
    "remaining_amount": "150.00",
    "pending_payments": {
      "total": "150.00",
      "count": 1
    }
  },
  "groups_detail": [
    {
      "id": "uuid",
      "group_name": "Math Grade 10",
      "enrollment_date": "2024-01-01",
      "effective_monthly_price": "180.00"
    }
  ]
}
```

### Update Student Remaining Sessions
```http
POST /api/students/students/{student_id}/update_remaining_sessions/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "sessions_to_add": 5
}
```

**Response:**
```json
{
  "message": "Added 5 sessions",
  "remaining_sessions": 13,
  "total_sessions_bought": 25
}
```

---

## Parents

### Get Parent Dashboard
```http
GET /api/parents/dashboard/
Authorization: Bearer {parent_token}
```

**Response:**
```json
{
  "parent_name": "Parent Name",
  "linked_students_count": 2,
  "students": [
    {
      "id": "uuid",
      "name": "Ahmed Ali",
      "code": "ST-1234567",
      "subscription_type": "monthly",
      "subscription_status": "active",
      "remaining_sessions": 8,
      "remaining_amount": "150.00",
      "monthly_attendance_rate": 85.5,
      "pending_payments_count": 1,
      "recent_grades": [
        {
          "grade_type": "Quiz",
          "grade": "85.00",
          "created_at": "2024-01-15T10:30:00Z"
        }
      ]
    }
  ]
}
```

### Get Student Details (Parent View)
```http
GET /api/parents/dashboard/student/{student_id}/
Authorization: Bearer {parent_token}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Ahmed Ali",
  "code": "ST-1234567",
  "subscription_type": "monthly",
  "attendance_summary": {
    "monthly_rate": 85.5
  },
  "payment_summary": {
    "remaining_amount": "150.00"
  },
  "permissions": {
    "can_view_grades": true,
    "can_view_attendance": true,
    "can_view_payments": true
  }
}
```

---

## Groups

### List Groups
```http
GET /api/groups/groups/?group_type=center&is_active=true
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 8,
  "results": [
    {
      "id": "uuid",
      "name": "Math Grade 10",
      "group_type": "center",
      "subject": "Mathematics",
      "max_students": 25,
      "students_count": 18,
      "monthly_price": "200.00",
      "session_price": "25.00",
      "is_active": true,
      "next_session_date": "2024-01-16"
    }
  ]
}
```

### Create Group
```http
POST /api/groups/groups/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "name": "Physics Grade 11",
  "description": "Advanced Physics Course",
  "group_type": "premium_center",
  "subject": "Physics",
  "grade_level": "Grade 11",
  "max_students": 20,
  "monthly_price": "300.00",
  "session_price": "40.00",
  "group_discount": "5.00",
  "sessions_per_month": 8,
  "session_duration_minutes": 90,
  "classroom": "Room A-101"
}
```

### Get Group Details
```http
GET /api/groups/groups/{group_id}/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Math Grade 10",
  "description": "Mathematics for Grade 10 students",
  "group_type": "center",
  "subject": "Mathematics",
  "max_students": 25,
  "current_students_count": 18,
  "monthly_price": "200.00",
  "students": [
    {
      "id": "uuid",
      "name": "Ahmed Ali",
      "code": "ST-1234567",
      "enrollment_date": "2024-01-01"
    }
  ],
  "schedules": [
    {
      "id": "uuid",
      "weekday": 1,
      "weekday_name": "Tuesday",
      "start_time": "14:00:00",
      "end_time": "15:30:00"
    }
  ],
  "statistics": {
    "monthly_attendance": {
      "total": 144,
      "present": 125,
      "absent": 19
    },
    "monthly_revenue": "3600.00",
    "attendance_rate": 86.8
  }
}
```

---

## Sessions

### List Sessions
```http
GET /api/sessions/sessions/?date=2024-01-15&group={group_id}
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid",
      "group_name": "Math Grade 10",
      "group_type": "center",
      "title": "Algebra Basics",
      "date": "2024-01-15",
      "start_time": "14:00:00",
      "end_time": "15:30:00",
      "status": "completed",
      "attendance_summary": {
        "total": 18,
        "present": 16,
        "absent": 2,
        "late": 0,
        "rate": 88.89
      }
    }
  ]
}
```

### Create Session
```http
POST /api/sessions/sessions/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "group": "uuid",
  "title": "Quadratic Equations",
  "description": "Introduction to quadratic equations",
  "date": "2024-01-20",
  "start_time": "14:00:00",
  "end_time": "15:30:00",
  "repeat_type": "weekly",
  "repeat_count": 8,
  "lesson_content": "Chapter 5: Quadratic Equations",
  "homework_assigned": "Exercise 5.1, problems 1-10"
}
```

### Get Session Schedule
```http
GET /api/sessions/sessions/schedule/?start_date=2024-01-15&end_date=2024-01-21
Authorization: Bearer {teacher_token}
```

**Response:**
```json
[
  {
    "date": "2024-01-15",
    "sessions": [
      {
        "id": "uuid",
        "group_name": "Math Grade 10",
        "title": "Algebra Basics",
        "start_time": "14:00:00",
        "end_time": "15:30:00",
        "status": "completed"
      }
    ],
    "total_sessions": 3,
    "completed_sessions": 2,
    "cancelled_sessions": 0
  }
]
```

### Start Session
```http
POST /api/sessions/sessions/{session_id}/start_session/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "in_progress",
  "actual_start_time": "14:02:00",
  "message": "Session started successfully"
}
```

### Take Attendance
```http
POST /api/sessions/sessions/{session_id}/take_attendance/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "attendance": [
    {
      "student_id": "uuid",
      "status": "present",
      "notes": ""
    },
    {
      "student_id": "uuid",
      "status": "absent",
      "notes": "Sick leave"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Attendance recorded: 15 new, 3 updated",
  "created": 15,
  "updated": 3
}
```

---

## Attendance

### List Attendance
```http
GET /api/attendance/attendance/?session__date=2024-01-15&student={student_id}
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 25,
  "results": [
    {
      "id": "uuid",
      "student_name": "Ahmed Ali",
      "student_code": "ST-1234567",
      "session_title": "Algebra Basics",
      "session_date": "2024-01-15",
      "session_time": "14:00:00",
      "status": "present",
      "method": "manual",
      "marked_at": "2024-01-15T14:05:00Z",
      "arrival_time": "14:02:00",
      "is_late": false
    }
  ]
}
```

### Bulk Create Attendance
```http
POST /api/attendance/attendance/bulk_create/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "session_id": "uuid",
  "attendance_records": [
    {
      "student_id": "uuid",
      "status": "present",
      "notes": ""
    },
    {
      "student_id": "uuid",
      "status": "late",
      "notes": "Traffic delay",
      "excuse_reason": "Transportation issue"
    }
  ]
}
```

### Generate QR Code for Attendance
```http
POST /api/attendance/attendance/generate_qr/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "session_id": "uuid"
}
```

**Response:**
```json
{
  "id": "uuid",
  "qr_token": "secure_qr_token",
  "qr_data": "{\"session_id\":\"uuid\",\"session_title\":\"Math Class\"}",
  "valid_until": "2024-01-15T16:00:00Z",
  "is_valid": true,
  "qr_url": "https://api.smartteacher.com/api/attendance/qr-scan/secure_qr_token/"
}
```

### QR Code Attendance Scan
```http
POST /api/attendance/qr-scan/{qr_token}/
Content-Type: application/json

{
  "student_code": "ST-1234567"
}
```

**Response:**
```json
{
  "message": "Attendance marked successfully",
  "student_name": "Ahmed Ali",
  "session_title": "Math Class",
  "status": "present",
  "marked_at": "2024-01-15T14:05:00Z"
}
```

### Get Attendance Statistics
```http
GET /api/attendance/attendance/statistics/?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "total": 450,
  "present": 380,
  "absent": 50,
  "late": 20,
  "excused": 0,
  "attendance_rate": 84.44,
  "punctuality_rate": 95.0
}
```

---

## Payments

### List Payments
```http
GET /api/payments/payments/?status=pending&student={student_id}
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 15,
  "results": [
    {
      "id": "uuid",
      "student_name": "Ahmed Ali",
      "student_code": "ST-1234567",
      "payment_type": "monthly",
      "amount": "200.00",
      "amount_paid": "150.00",
      "remaining_amount": "50.00",
      "payment_method": "cash",
      "status": "partial",
      "due_date": "2024-01-15",
      "payment_date": "2024-01-10",
      "period_start": "2024-01-01",
      "period_end": "2024-01-31",
      "reference_number": "PAY-20240115-1234",
      "is_overdue": false,
      "days_overdue": 0
    }
  ]
}
```

### Create Payment
```http
POST /api/payments/payments/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "student": "uuid",
  "payment_type": "monthly",
  "amount": "200.00",
  "payment_method": "cash",
  "due_date": "2024-02-15",
  "period_start": "2024-02-01",
  "period_end": "2024-02-29",
  "notes": "February monthly payment"
}
```

### Add Payment Amount
```http
POST /api/payments/payments/{payment_id}/add_payment/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "amount": "50.00",
  "payment_method": "bank_transfer",
  "notes": "Partial payment received",
  "transaction_reference": "TXN123456"
}
```

**Response:**
```json
{
  "id": "uuid",
  "amount_paid": "200.00",
  "remaining_amount": "0.00",
  "status": "paid",
  "payment_date": "2024-01-15",
  "message": "Payment added successfully"
}
```

### Apply Discount
```http
POST /api/payments/payments/{payment_id}/apply_discount/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "discount_amount": "20.00",
  "reason": "Early payment discount"
}
```

### Get Overdue Payments
```http
GET /api/payments/payments/overdue/
Authorization: Bearer {teacher_token}
```

### Get Payment Summary
```http
GET /api/payments/payments/summary/?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "total_payments": 45,
  "total_amount": "9000.00",
  "total_paid": "7500.00",
  "total_pending": "1200.00",
  "total_overdue": "300.00",
  "pending_count": 8,
  "overdue_count": 3,
  "paid_count": 34
}
```

### Bulk Payment Actions
```http
POST /api/payments/payments/bulk_action/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "payment_ids": ["uuid1", "uuid2", "uuid3"],
  "action": "mark_paid",
  "payment_method": "cash",
  "notes": "Bulk payment processing"
}
```

---

## Receipts

### List Receipts
```http
GET /api/receipts/receipts/?status=generated&payment__student={student_id}
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 20,
  "results": [
    {
      "id": "uuid",
      "student_name": "Ahmed Ali",
      "student_code": "ST-1234567",
      "receipt_number": "RCP-20240115-1234",
      "receipt_type": "payment",
      "status": "generated",
      "title": "Payment Receipt - Ahmed Ali",
      "payment_amount": "200.00",
      "payment_type": "Monthly Subscription",
      "pdf_file": "/media/receipts/receipt_RCP-20240115-1234.pdf",
      "pdf_url": "https://api.smartteacher.com/media/receipts/receipt_RCP-20240115-1234.pdf",
      "pdf_generated_at": "2024-01-15T10:30:00Z",
      "sent_at": null,
      "created_at": "2024-01-15T10:25:00Z"
    }
  ]
}
```

### Create Receipt
```http
POST /api/receipts/receipts/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "payment": "uuid",
  "receipt_type": "payment",
  "title": "Monthly Payment Receipt",
  "description": "Payment for January 2024"
}
```

### Generate PDF
```http
POST /api/receipts/receipts/{receipt_id}/generate_pdf/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "generated",
  "pdf_file": "/media/receipts/receipt_RCP-20240115-1234.pdf",
  "pdf_generated_at": "2024-01-15T10:30:00Z",
  "message": "PDF generated successfully"
}
```

### Send Receipt
```http
POST /api/receipts/receipts/{receipt_id}/send_receipt/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "email": "parent@example.com",
  "via_whatsapp": true
}
```

### Download Receipt PDF
```http
GET /api/receipts/receipts/{receipt_id}/download_pdf/
Authorization: Bearer {teacher_token}
```

**Response:** PDF file download

### Bulk Generate Receipts
```http
POST /api/receipts/receipts/bulk_generate/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "payment_ids": ["uuid1", "uuid2", "uuid3"],
  "receipt_type": "payment",
  "auto_generate_pdf": true
}
```

### Generate Monthly Receipts
```http
POST /api/receipts/receipts/generate_monthly/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "year": 2024,
  "month": 1,
  "auto_generate_pdf": true
}
```

---

## Grades

### List Grades
```http
GET /api/grades/grades/?student={student_id}&grade_type={grade_type_id}
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 30,
  "results": [
    {
      "id": "uuid",
      "student_name": "Ahmed Ali",
      "student_code": "ST-1234567",
      "grade_type_name": "Quiz",
      "grade_type_color": "#17a2b8",
      "session_title": "Algebra Basics",
      "title": "Quiz 1 - Linear Equations",
      "description": "First quiz on linear equations",
      "score": "85.00",
      "max_score": "100.00",
      "percentage": "85.00",
      "letter_grade": "B+",
      "grade_date": "2024-01-15",
      "grade_status": "Very Good",
      "is_published": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Grade
```http
POST /api/grades/grades/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "student": "uuid",
  "grade_type": "uuid",
  "session": "uuid",
  "title": "Midterm Exam - Algebra",
  "description": "Comprehensive algebra midterm examination",
  "score": "92.50",
  "max_score": "100.00",
  "grade_date": "2024-01-15",
  "notes": "Excellent performance in problem solving",
  "feedback": "Great work! Focus on showing more steps in solutions.",
  "is_published": true
}
```

### Bulk Create Grades
```http
POST /api/grades/grades/bulk_create/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "grades": [
    {
      "student_id": "uuid1",
      "grade_type_id": "uuid",
      "title": "Quiz 2",
      "score": "88.00",
      "max_score": "100.00",
      "grade_date": "2024-01-15"
    },
    {
      "student_id": "uuid2",
      "grade_type_id": "uuid",
      "title": "Quiz 2",
      "score": "76.50",
      "max_score": "100.00",
      "grade_date": "2024-01-15"
    }
  ]
}
```

### Add Grade Comment
```http
POST /api/grades/grades/{grade_id}/add_comment/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "comment": "Student showed significant improvement in this assessment.",
  "is_private": false
}
```

### Get Grade Statistics
```http
GET /api/grades/grades/statistics/?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "total_grades": 150,
  "average_score": "82.45",
  "average_percentage": "82.45",
  "highest_score": "98.50",
  "lowest_score": "45.00",
  "grade_distribution": {
    "A+": 15,
    "A": 25,
    "B+": 30,
    "B": 35,
    "C+": 25,
    "C": 15,
    "D+": 3,
    "D": 2,
    "F": 0
  },
  "grade_type_breakdown": [
    {
      "grade_type__name": "Quiz",
      "count": 60,
      "avg_percentage": "78.50"
    },
    {
      "grade_type__name": "Exam",
      "count": 30,
      "avg_percentage": "85.20"
    }
  ]
}
```

### Generate Student Grade Report
```http
POST /api/grades/grades/generate_report/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "student_id": "uuid",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "grade_types": ["uuid1", "uuid2"],
  "include_comments": true,
  "include_summary": true
}
```

### Grade Types Management
```http
GET /api/grades/grade-types/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 4,
  "results": [
    {
      "id": "uuid",
      "name": "Quiz",
      "description": "Short quizzes",
      "max_score": "100.00",
      "weight": "0.20",
      "color": "#17a2b8",
      "grades_count": 45,
      "is_active": true
    }
  ]
}
```

### Create Default Grade Types
```http
POST /api/grades/grade-types/create_default_types/
Authorization: Bearer {teacher_token}
```

---

## Reports

### Generate Student Report
```http
POST /api/reports/reports/student_report/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "student_id": "uuid",
  "report_type": "comprehensive",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "include_attendance": true,
  "include_grades": true,
  "include_payments": true,
  "format": "pdf"
}
```

**Response:**
```json
{
  "report_id": "uuid",
  "status": "generating",
  "download_url": null,
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

### Get Report Status
```http
GET /api/reports/reports/{report_id}/status/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "completed",
  "download_url": "https://api.smartteacher.com/media/reports/student_report_uuid.pdf",
  "generated_at": "2024-01-15T10:33:00Z",
  "expires_at": "2024-01-22T10:33:00Z"
}
```

### Financial Report
```http
GET /api/reports/reports/financial/?start_date=2024-01-01&end_date=2024-01-31&format=json
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "summary": {
    "total_revenue": "15000.00",
    "total_payments": 75,
    "pending_amount": "2500.00",
    "overdue_amount": "500.00"
  },
  "by_payment_type": {
    "monthly": {
      "count": 45,
      "total": "12000.00"
    },
    "session": {
      "count": 30,
      "total": "3000.00"
    }
  },
  "by_student": [
    {
      "student_name": "Ahmed Ali",
      "total_paid": "400.00",
      "pending": "0.00"
    }
  ]
}
```

---

## Notifications

### List Notifications
```http
GET /api/notifications/notifications/?status=pending&notification_type=payment
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 25,
  "results": [
    {
      "id": "uuid",
      "recipient_type": "student",
      "recipient_name": "Ahmed Ali",
      "title": "Payment Reminder",
      "message": "Your monthly payment of 200.00 SAR is due tomorrow.",
      "notification_type": "payment",
      "channel": "whatsapp",
      "status": "pending",
      "scheduled_at": "2024-01-16T09:00:00Z",
      "sent_at": null,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Notification
```http
POST /api/notifications/notifications/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "recipient_type": "student",
  "recipient_id": "uuid",
  "title": "Session Reminder",
  "message": "Your Math class starts in 1 hour at 2:00 PM.",
  "notification_type": "session",
  "channel": "whatsapp",
  "scheduled_at": "2024-01-16T13:00:00Z"
}
```

### Send Notification
```http
POST /api/notifications/notifications/{notification_id}/send/
Authorization: Bearer {teacher_token}
```

### Bulk Send Notifications
```http
POST /api/notifications/notifications/bulk_send/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "notification_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Create Bulk Notifications
```http
POST /api/notifications/notifications/bulk_create/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "recipient_type": "student",
  "recipient_ids": ["uuid1", "uuid2", "uuid3"],
  "title": "Important Announcement",
  "message": "Classes will resume on January 20th after the holiday break.",
  "notification_type": "announcement",
  "channel": "whatsapp"
}
```

---

## Smart Insights

### Get Dashboard Analytics
```http
GET /api/insights/analytics/dashboard/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "overview": {
    "total_students": 45,
    "active_students": 42,
    "total_revenue": "15000.00",
    "attendance_rate": 87.5
  },
  "trends": {
    "student_growth": [
      {"month": "2024-01", "count": 40},
      {"month": "2024-02", "count": 45}
    ],
    "revenue_trend": [
      {"month": "2024-01", "amount": "12000.00"},
      {"month": "2024-02", "amount": "15000.00"}
    ]
  },
  "alerts_summary": {
    "total_active": 8,
    "high_priority": 3,
    "by_type": {
      "attendance": 3,
      "payment": 4,
      "grade": 1
    }
  }
}
```

### Get Insights
```http
GET /api/insights/insights/?category=attendance&priority=high
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid",
      "category": "attendance",
      "priority": "high",
      "title": "Low Attendance Alert",
      "description": "3 students have attendance rate below 70%",
      "insight_data": {
        "affected_students": ["uuid1", "uuid2", "uuid3"],
        "average_rate": 65.5,
        "recommendation": "Schedule parent meetings"
      },
      "action_taken": false,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Get Alerts
```http
GET /api/insights/alerts/?is_active=true&severity=high
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 8,
  "results": [
    {
      "id": "uuid",
      "alert_type": "low_attendance",
      "severity": "high",
      "title": "Student Attendance Alert",
      "message": "Ahmed Ali has missed 4 consecutive sessions",
      "target_type": "student",
      "target_id": "uuid",
      "trigger_data": {
        "student_name": "Ahmed Ali",
        "consecutive_absences": 4,
        "last_attendance": "2024-01-10"
      },
      "is_active": true,
      "is_resolved": false,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Resolve Alert
```http
POST /api/insights/alerts/{alert_id}/resolve/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "resolution_notes": "Contacted parent, student will return next week"
}
```

### Get Suggestions
```http
GET /api/insights/suggestions/?category=financial&is_active=true
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": "uuid",
      "category": "financial",
      "priority": "medium",
      "title": "Payment Collection Optimization",
      "description": "Consider offering early payment discounts to improve cash flow",
      "suggestion_data": {
        "potential_impact": "15% faster payment collection",
        "implementation_effort": "low"
      },
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Rules Engine

### List Rules
```http
GET /api/rules/rules/?rule_type=attendance&is_active=true
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 12,
  "results": [
    {
      "id": "uuid",
      "name": "Consecutive Absence Alert",
      "description": "Alert when student misses 3 consecutive sessions",
      "rule_type": "attendance",
      "conditions": {
        "consecutive_absences": 3
      },
      "actions": [
        {
          "type": "create_alert",
          "severity": "high"
        },
        {
          "type": "send_notification",
          "channel": "whatsapp"
        }
      ],
      "is_active": true,
      "priority": 1,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Rule
```http
POST /api/rules/rules/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "name": "Low Grade Alert",
  "description": "Alert when student grade falls below 60%",
  "rule_type": "grade",
  "conditions": {
    "grade_percentage": {"lt": 60}
  },
  "actions": [
    {
      "type": "create_alert",
      "severity": "medium",
      "message": "Student {{student_name}} scored {{grade_percentage}}% in {{grade_type}}"
    }
  ],
  "is_active": true,
  "priority": 2
}
```

### Test Rule
```http
POST /api/rules/rules/{rule_id}/test/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "test_data": {
    "student_id": "uuid",
    "grade_percentage": 55
  }
}
```

**Response:**
```json
{
  "rule_triggered": true,
  "actions_executed": [
    {
      "type": "create_alert",
      "status": "success",
      "alert_id": "uuid"
    }
  ],
  "test_results": {
    "conditions_met": true,
    "execution_time": "0.05s"
  }
}
```

### Get Rule Execution History
```http
GET /api/rules/executions/?rule={rule_id}&start_date=2024-01-01
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 25,
  "results": [
    {
      "id": "uuid",
      "rule_name": "Consecutive Absence Alert",
      "trigger_data": {
        "student_id": "uuid",
        "student_name": "Ahmed Ali",
        "consecutive_absences": 3
      },
      "actions_executed": [
        {
          "type": "create_alert",
          "status": "success"
        }
      ],
      "execution_status": "success",
      "executed_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Settings

### Get Settings
```http
GET /api/settings/settings/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "app_identity": {
    "center_name": "My Learning Center",
    "teacher_name": "Prof. Ahmed",
    "logo_url": "https://api.smartteacher.com/media/logos/center_logo.png"
  },
  "preferences": {
    "language": "ar",
    "theme": "light",
    "currency": "SAR",
    "timezone": "Asia/Riyadh"
  },
  "subscription": {
    "plan": "premium",
    "max_students": 100,
    "max_groups": 20,
    "expires_at": "2024-12-31T23:59:59Z"
  },
  "notifications": {
    "email_enabled": true,
    "whatsapp_enabled": true,
    "push_enabled": true
  },
  "smart_alerts": {
    "attendance_alerts": true,
    "payment_alerts": true,
    "grade_alerts": true,
    "thresholds": {
      "low_attendance_rate": 70,
      "consecutive_absences": 3,
      "overdue_payment_days": 7
    }
  }
}
```

### Update Settings
```http
PUT /api/settings/settings/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "app_identity": {
    "center_name": "Updated Center Name",
    "teacher_name": "Prof. Ahmed Ali"
  },
  "preferences": {
    "language": "en",
    "theme": "dark"
  },
  "smart_alerts": {
    "thresholds": {
      "low_attendance_rate": 75,
      "consecutive_absences": 2
    }
  }
}
```

### Reset Data (Danger Zone)
```http
POST /api/settings/settings/reset_data/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "reset_type": "students",  // or "sessions", "payments", "grades", "all"
  "confirmation_text": "DELETE ALL STUDENTS"
}
```

**Response:**
```json
{
  "message": "Data reset completed successfully",
  "reset_type": "students",
  "items_deleted": 45,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Subscriptions

### Get Current Subscription
```http
GET /api/subscriptions/subscription/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "plan": "premium",
  "status": "active",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "limits": {
    "max_students": 100,
    "max_groups": 20,
    "storage_gb": 10
  },
  "usage": {
    "current_students": 45,
    "current_groups": 8,
    "storage_used_gb": 2.5
  },
  "features": [
    "smart_insights",
    "advanced_reports",
    "whatsapp_integration",
    "bulk_operations"
  ],
  "next_billing_date": "2024-02-01",
  "amount": "99.00"
}
```

### Get Available Plans
```http
GET /api/subscriptions/plans/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 4,
  "results": [
    {
      "id": "uuid",
      "name": "Free",
      "price": "0.00",
      "billing_cycle": "monthly",
      "limits": {
        "max_students": 20,
        "max_groups": 5,
        "storage_gb": 1
      },
      "features": [
        "basic_management",
        "attendance_tracking"
      ]
    },
    {
      "id": "uuid",
      "name": "Premium",
      "price": "99.00",
      "billing_cycle": "monthly",
      "limits": {
        "max_students": 100,
        "max_groups": 20,
        "storage_gb": 10
      },
      "features": [
        "smart_insights",
        "advanced_reports",
        "whatsapp_integration",
        "bulk_operations"
      ]
    }
  ]
}
```

---

## Exports

### Export Students
```http
POST /api/exports/exports/students/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "format": "csv",  // or "excel", "pdf"
  "filters": {
    "subscription_type": "monthly",
    "is_active": true
  },
  "fields": [
    "name", "code", "phone", "subscription_type", 
    "remaining_amount", "attendance_rate"
  ]
}
```

**Response:**
```json
{
  "export_id": "uuid",
  "status": "processing",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

### Get Export Status
```http
GET /api/exports/exports/{export_id}/status/
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "id": "uuid",
  "export_type": "students",
  "status": "completed",
  "download_url": "https://api.smartteacher.com/media/exports/students_export_uuid.csv",
  "file_size": "125KB",
  "records_count": 45,
  "generated_at": "2024-01-15T10:33:00Z",
  "expires_at": "2024-01-22T10:33:00Z"
}
```

### Download Export
```http
GET /api/exports/exports/{export_id}/download/
Authorization: Bearer {teacher_token}
```

**Response:** File download (CSV/Excel/PDF)

### Export Payments
```http
POST /api/exports/exports/payments/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "format": "excel",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "include_transactions": true
}
```

### Export Attendance
```http
POST /api/exports/exports/attendance/
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "format": "csv",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "group_id": "uuid"
}
```

---

## Sync

### Get Sync Status
```http
GET /api/sync/status/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "last_sync": "2024-01-15T10:30:00Z",
  "sync_status": "completed",
  "pending_changes": 0,
  "conflicts": 0,
  "next_sync": "2024-01-15T11:00:00Z"
}
```

### Push Changes
```http
POST /api/sync/push/
Authorization: Bearer {token}
Content-Type: application/json

{
  "changes": [
    {
      "id": "local_uuid",
      "model": "students.Student",
      "action": "create",
      "data": {
        "name": "New Student",
        "phone": "+966501234567"
      },
      "timestamp": "2024-01-15T10:25:00Z"
    },
    {
      "id": "uuid",
      "model": "attendance.Attendance",
      "action": "update",
      "data": {
        "status": "present",
        "notes": "Updated attendance"
      },
      "timestamp": "2024-01-15T10:28:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "processed": 2,
  "conflicts": 0,
  "errors": 0,
  "results": [
    {
      "local_id": "local_uuid",
      "server_id": "uuid",
      "status": "created"
    },
    {
      "local_id": "uuid",
      "server_id": "uuid",
      "status": "updated"
    }
  ]
}
```

### Pull Changes
```http
GET /api/sync/pull/?since=2024-01-15T10:00:00Z
Authorization: Bearer {token}
```

**Response:**
```json
{
  "changes": [
    {
      "id": "uuid",
      "model": "payments.Payment",
      "action": "create",
      "data": {
        "student": "uuid",
        "amount": "200.00",
        "status": "paid"
      },
      "timestamp": "2024-01-15T10:32:00Z"
    }
  ],
  "has_more": false,
  "next_cursor": null
}
```

### Resolve Conflicts
```http
POST /api/sync/resolve_conflicts/
Authorization: Bearer {token}
Content-Type: application/json

{
  "resolutions": [
    {
      "conflict_id": "uuid",
      "resolution": "server_wins"  // or "client_wins", "merge"
    }
  ]
}
```

---

## Audit Logs

### Get Audit Logs
```http
GET /api/audit/logs/?action=create&model=students.Student&start_date=2024-01-01
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "count": 150,
  "results": [
    {
      "id": "uuid",
      "user": "teacher_username",
      "action": "create",
      "model": "students.Student",
      "object_id": "uuid",
      "object_repr": "Ahmed Ali (ST-1234567)",
      "changes": {
        "name": "Ahmed Ali",
        "phone": "+966501234567",
        "subscription_type": "monthly"
      },
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Get Activity Summary
```http
GET /api/audit/activity_summary/?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {teacher_token}
```

**Response:**
```json
{
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "total_actions": 1250,
  "by_action": {
    "create": 450,
    "update": 650,
    "delete": 150
  },
  "by_model": {
    "students.Student": 200,
    "attendance.Attendance": 500,
    "payments.Payment": 300
  },
  "most_active_days": [
    {
      "date": "2024-01-15",
      "actions": 85
    }
  ]
}
```

---

## WebSocket Events (Real-time Updates)

### Connection
```javascript
const ws = new WebSocket('wss://api.smartteacher.com/ws/updates/');
ws.onopen = function() {
    // Send authentication
    ws.send(JSON.stringify({
        'type': 'auth',
        'token': 'jwt_token_here'
    }));
};
```

### Event Types
```json
{
  "type": "attendance_marked",
  "data": {
    "session_id": "uuid",
    "student_name": "Ahmed Ali",
    "status": "present"
  }
}

{
  "type": "payment_received",
  "data": {
    "payment_id": "uuid",
    "student_name": "Ahmed Ali",
    "amount": "200.00"
  }
}

{
  "type": "alert_created",
  "data": {
    "alert_id": "uuid",
    "title": "Low Attendance Alert",
    "severity": "high"
  }
}
```

---

## Rate Limiting

All API endpoints are rate limited:
- **Teachers**: 1000 requests per hour
- **Students/Parents**: 500 requests per hour
- **Bulk operations**: 100 requests per hour

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

---

## API Versioning

Current version: `v1`

Version can be specified in:
1. **URL**: `/api/v1/students/`
2. **Header**: `Accept: application/vnd.smartteacher.v1+json`

---

## Error Codes Reference

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Invalid login credentials |
| `PERMISSION_DENIED` | Insufficient permissions |
| `STUDENT_NOT_FOUND` | Student does not exist |
| `PAYMENT_ALREADY_PAID` | Payment is already completed |
| `SESSION_EXPIRED` | Authentication session expired |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `VALIDATION_ERROR` | Request data validation failed |
| `SYNC_CONFLICT` | Data synchronization conflict |

---

This API contract provides comprehensive documentation for all endpoints in the Smart Teacher Assistant backend system. Each endpoint includes request/response examples, authentication requirements, and error handling information.