import json
import uuid

# Base URL variable
base_url_var = "{{base_url}}"

def create_request(name, method, url_path, body=None, query_params=None, description=""):
    request = {
        "method": method,
        "header": [
            {
                "key": "Content-Type",
                "value": "application/json",
                "type": "text"
            },
            {
                "key": "Authorization",
                "value": "Bearer {{token}}",
                "type": "text"
            }
        ],
        "url": {
            "raw": f"{base_url_var}/{url_path}",
            "host": [base_url_var],
            "path": url_path.split("/")
        },
        "description": description
    }
    
    if query_params:
        request["url"]["query"] = query_params

    if body:
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=4),
            "options": {
                "raw": {
                    "language": "json"
                }
            }
        }
    return {
        "name": name,
        "request": request,
        "response": []
    }

items = []

# ==========================================
# 1. Authentication & Accounts
# ==========================================
auth_items = [
    create_request("Teacher Login", "POST", "auth/teacher-login/", 
                  {"pin": "1234", "device_info": {"device_type": "mobile"}}),
    create_request("Student Login", "POST", "auth/student-login/", 
                  {"student_code": "ST-12345"}),
    create_request("Teacher Logout", "POST", "auth/teacher-logout/"),
    create_request("Get Profile", "GET", "auth/profile/"),
    create_request("Update Profile", "PUT", "auth/profile/", 
                  {"email": "updated@example.com"}),
    create_request("Generate Student QR", "POST", "auth/generate-student-qr/", 
                  {"student_id": "{{student_id}}"}),
    create_request("Session Status", "GET", "auth/session-status/"),
    create_request("Extend Session", "POST", "auth/extend-session/")
]
# Remove Auth header from Login requests
auth_items[0]['request']['header'] = [{"key": "Content-Type", "value": "application/json", "type": "text"}]
auth_items[1]['request']['header'] = [{"key": "Content-Type", "value": "application/json", "type": "text"}]

items.append({"name": "Authentication", "item": auth_items})

# ==========================================
# 2. Teachers
# ==========================================
items.append({
    "name": "Teachers",
    "item": [
        create_request("Dashboard", "GET", "teachers/profile/dashboard/"),
        create_request("Stats", "GET", "teachers/profile/stats/"),
        create_request("Profile List", "GET", "teachers/profile/"), # ViewSet
        create_request("Profile Detail", "GET", "teachers/profile/{{teacher_id}}/")
    ]
})

# ==========================================
# 3. Students
# ==========================================
student_actions = [
    create_request("List Students", "GET", "students/"),
    create_request("Create Student", "POST", "students/",
                  {"name": "New Student", "phone": "+966500000000", "subscription_type": "monthly", "monthly_price": "200.00", "grade_level": "10"}),
    create_request("Get Student", "GET", "students/{{student_id}}/"),
    create_request("Update Student", "PATCH", "students/{{student_id}}/", {"name": "Updated Name"}),
    create_request("Delete Student", "DELETE", "students/{{student_id}}/"),
    create_request("Detailed Profile", "GET", "students/{{student_id}}/profile/"),
    create_request("Update Remaining Sessions", "POST", "students/{{student_id}}/update_remaining_sessions/", {"sessions_to_add": 5}),
    create_request("Update Subscription", "POST", "students/{{student_id}}/update_subscription/", {"subscription_type": "monthly"}),
    create_request("Attendance History", "GET", "students/{{student_id}}/attendance_history/"),
    create_request("Payment History", "GET", "students/{{student_id}}/payment_history/"),
    create_request("Grades History", "GET", "students/{{student_id}}/grades_history/"),
    create_request("Statistics", "GET", "students/statistics/")
]

parent_sub = [
    create_request("List Parents", "GET", "students/parents/"),
    create_request("Create Parent", "POST", "students/parents/", {"name": "Parent Name", "phone": "+966500000001"}),
    create_request("Get Parent", "GET", "students/parents/{{parent_id}}/"),
    create_request("Linked Students", "GET", "students/parents/{{parent_id}}/linked_students/")
]

link_sub = [
    create_request("List Links", "GET", "students/student-parent-links/"),
    create_request("Create Link", "POST", "students/student-parent-links/", {"student": "{{student_id}}", "parent": "{{parent_id}}"})
]

group_enroll_sub = [
    create_request("List Enrollments", "GET", "students/student-groups/"),
    create_request("Enroll Student", "POST", "students/student-groups/", {"student": "{{student_id}}", "group": "{{group_id}}"})
]

items.append({
    "name": "Students Management",
    "item": [
        {"name": "Students", "item": student_actions},
        {"name": "Parents", "item": parent_sub},
        {"name": "Student-Parent Links", "item": link_sub},
        {"name": "Group Enrollments", "item": group_enroll_sub}
    ]
})

# ==========================================
# 4. Parents App
# ==========================================
items.append({
    "name": "Parents App",
    "item": [
        create_request("Dashboard", "GET", "parents/dashboard/")
    ]
})

# ==========================================
# 5. Groups
# ==========================================
group_actions = [
    create_request("List Groups", "GET", "groups/"),
    create_request("Create Group", "POST", "groups/", 
                  {"name": "Math Group", "subject": "Math", "level": "Grade 10", "capacity": 20}),
    create_request("Get Group", "GET", "groups/{{group_id}}/"),
    create_request("Get Students in Group", "GET", "groups/{{group_id}}/students/"),
    create_request("Add Student", "POST", "groups/{{group_id}}/add_student/", {"student_id": "{{student_id}}"}),
    create_request("Remove Student", "POST", "groups/{{group_id}}/remove_student/", {"student_id": "{{student_id}}"}),
    create_request("Statistics", "GET", "groups/{{group_id}}/statistics/")
]

schedule_sub = [
    create_request("List Schedules", "GET", "groups/schedules/"),
    create_request("Create Schedule", "POST", "groups/schedules/", 
                  {"group": "{{group_id}}", "weekday": 0, "start_time": "10:00", "end_time": "11:30"})
]

material_sub = [
    create_request("List Materials", "GET", "groups/materials/"),
    create_request("Create Material", "POST", "groups/materials/", 
                  {"group": "{{group_id}}", "title": "Syllabus", "material_type": "document"})
]

announce_sub = [
    create_request("List Announcements", "GET", "groups/announcements/"),
    create_request("Create Announcement", "POST", "groups/announcements/", 
                  {"group": "{{group_id}}", "title": "Welcome", "content": "Welcome to class"})
]

items.append({
    "name": "Groups Management",
    "item": [
        {"name": "Groups", "item": group_actions},
        {"name": "Schedules", "item": schedule_sub},
        {"name": "Materials", "item": material_sub},
        {"name": "Announcements", "item": announce_sub}
    ]
})

# ==========================================
# 6. Sessions
# ==========================================
session_actions = [
    create_request("List Sessions", "GET", "sessions/"),
    create_request("Create Session", "POST", "sessions/",
                  {"group": "{{group_id}}", "date": "2024-03-20", "start_time": "10:00", "end_time": "11:30"}),
    create_request("Get Session", "GET", "sessions/{{session_id}}/"),
    create_request("Start Session", "POST", "sessions/{{session_id}}/start_session/"),
    create_request("End Session", "POST", "sessions/{{session_id}}/end_session/"),
    create_request("Cancel Session", "POST", "sessions/{{session_id}}/cancel_session/", {"reason": "Sick leave"}),
    create_request("Get Attendance", "GET", "sessions/{{session_id}}/attendance/"),
    create_request("Take Attendance", "POST", "sessions/{{session_id}}/take_attendance/", 
                  {"attendance": [{"student_id": "{{student_id}}", "status": "present"}]}),
    create_request("Get Schedule", "GET", "sessions/schedule/"),
    create_request("Get Today's Sessions", "GET", "sessions/today/"),
    create_request("Get Upcoming Sessions", "GET", "sessions/upcoming/"),
    create_request("Statistics", "GET", "sessions/statistics/")
]

items.append({
    "name": "Sessions",
    "item": [
        {"name": "Sessions", "item": session_actions},
        {"name": "Reminders", "item": [create_request("List Reminders", "GET", "sessions/reminders/")]},
        {"name": "Materials", "item": [create_request("List Session Materials", "GET", "sessions/materials/")]},
        {"name": "Notes", "item": [create_request("List Session Notes", "GET", "sessions/notes/")]}
    ]
})

# ==========================================
# 7. Attendance
# ==========================================
items.append({
    "name": "Attendance",
    "item": [
        create_request("List Attendance", "GET", "attendance/"),
        create_request("Create Record", "POST", "attendance/", 
                      {"session": "{{session_id}}", "student": "{{student_id}}", "status": "present"})
    ]
})

# ==========================================
# 8. Financials (Payments & Receipts)
# ==========================================
payment_actions = [
    create_request("List Payments", "GET", "payments/"),
    create_request("Create Payment", "POST", "payments/", 
                  {"student": "{{student_id}}", "amount": "200.00", "payment_type": "monthly", "period_start": "2024-03-01", "period_end": "2024-03-31"}),
    create_request("Payment Summary", "GET", "payments/summary/") # Assuming standard list URL with query param or if custom action exists
]

receipt_actions = [
    create_request("List Receipts", "GET", "receipts/"),
    create_request("Create Receipt", "POST", "receipts/", {"payment": "{{payment_id}}"}),
    create_request("Generate PDF", "POST", "receipts/{{receipt_id}}/generate_pdf/")
]

items.append({
    "name": "Financials",
    "item": [
        {"name": "Payments", "item": payment_actions},
        {"name": "Receipts", "item": receipt_actions}
    ]
})

# ==========================================
# 9. Grades
# ==========================================
items.append({
    "name": "Grades",
    "item": [
        {"name": "Grades", "item": [
            create_request("List Grades", "GET", "grades/"),
            create_request("Create Grade", "POST", "grades/", 
                          {"student": "{{student_id}}", "grade_type": "{{grade_type_id}}", "score": 90})
        ]},
        {"name": "Grade Types", "item": [
            create_request("List Types", "GET", "grades/grade-types/"),
            create_request("Create Type", "POST", "grades/grade-types/", {"name": "Test", "weight": 20})
        ]},
        {"name": "Scales", "item": [create_request("List Scales", "GET", "grades/scales/")]},
        {"name": "Summaries", "item": [create_request("List Summaries", "GET", "grades/summaries/")]},
        {"name": "Alerts", "item": [create_request("List Alerts", "GET", "grades/alerts/")]}
    ]
})

# ==========================================
# 10. Notifications
# ==========================================
items.append({
    "name": "Notifications",
    "item": [
        {"name": "Notifications", "item": [create_request("List Notifications", "GET", "notifications/")]},
        {"name": "Templates", "item": [create_request("List Templates", "GET", "notifications/templates/")]},
        {"name": "Batches", "item": [create_request("List Batches", "GET", "notifications/batches/")]}
    ]
})

# ==========================================
# 11. Reports & Analytics (Smart Insights)
# ==========================================
items.append({
    "name": "Reports & Insights",
    "item": [
        {"name": "Reports", "item": [create_request("List Reports", "GET", "reports/reports/")]},
        {"name": "Insights", "item": [
            create_request("List Insights", "GET", "insights/insights/"),
            create_request("Alerts", "GET", "insights/alerts/"),
            create_request("Suggestions", "GET", "insights/suggestions/"),
            create_request("Analytics", "GET", "insights/analytics/"),
            create_request("Widgets", "GET", "insights/widgets/")
        ]}
    ]
})

# ==========================================
# 12. System & Settings
# ==========================================
items.append({
    "name": "System & Settings",
    "item": [
        {"name": "Settings", "item": [create_request("List Settings", "GET", "settings/settings/")]},
        {"name": "Audit Logs", "item": [create_request("List Logs", "GET", "audit/logs/")]},
        {"name": "Exports", "item": [create_request("List Exports", "GET", "exports/exports/")]},
        {"name": "Sync", "item": [create_request("List Sync", "GET", "sync/")]},
        {"name": "Rules Engine", "item": [
            create_request("Rules", "GET", "rules/rules/"),
            create_request("Executions", "GET", "rules/executions/"),
            create_request("Templates", "GET", "rules/templates/"),
            create_request("Rule Sets", "GET", "rules/rule-sets/")
        ]},
        {"name": "Subscriptions", "item": [
            create_request("My Subscription", "GET", "subscriptions/"),
            create_request("Plans", "GET", "subscriptions/plans/")
        ]}
    ]
})

collection = {
    "info": {
        "name": "Smart Teacher Assistant API (All Endpoints)",
        "description": "Comprehensive API collection covering all implemented modules.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": items,
    "variable": [
        {"key": "base_url", "value": "http://localhost:8000/api", "type": "string"},
        {"key": "token", "value": "", "type": "string"},
        {"key": "teacher_id", "value": "", "type": "string"},
        {"key": "student_id", "value": "", "type": "string"},
        {"key": "parent_id", "value": "", "type": "string"},
        {"key": "group_id", "value": "", "type": "string"},
        {"key": "session_id", "value": "", "type": "string"},
        {"key": "payment_id", "value": "", "type": "string"},
        {"key": "receipt_id", "value": "", "type": "string"},
        {"key": "grade_type_id", "value": "", "type": "string"}
    ]
}

with open('smart_teacher_assistant_full.postman_collection.json', 'w') as f:
    json.dump(collection, f, indent=4)

print("Full Postman collection generated: smart_teacher_assistant_full.postman_collection.json")
