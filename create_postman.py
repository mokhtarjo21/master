import json
import uuid

collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "Teacher Auth & Bulk Payments",
        "description": "APIs for Teacher Registration (PIN & Google), Login, and Bulk Payments",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Authentication",
            "item": [
                {
                    "name": "1. Teacher Registration (PIN)",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Content-Type", "value": "application/json"}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "username": "teacher_kamel",
                                "email": "kamel@example.com",
                                "pin": "1234",
                                "center_name": "Kamel Center",
                                "first_name": "Ahmed",
                                "last_name": "Kamel",
                                "language": "ar"
                            }, indent=4)
                        },
                        "url": {
                            "raw": "{{base_url}}/api/auth/teacher-register/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "auth", "teacher-register", ""]
                        }
                    }
                },
                {
                    "name": "2. Teacher Google Login/Signup",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Content-Type", "value": "application/json"}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "id_token": "ENTER_YOUR_VALID_GOOGLE_ID_TOKEN_HERE",
                                "device_info": {"os": "Windows", "browser": "Chrome"}
                            }, indent=4)
                        },
                        "url": {
                            "raw": "{{base_url}}/api/auth/teacher-google-login/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "auth", "teacher-google-login", ""]
                        }
                    }
                },
                {
                    "name": "3. Teacher Login (PIN)",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Content-Type", "value": "application/json"}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "pin": "1234",
                                "device_info": {}
                            }, indent=4)
                        },
                        "url": {
                            "raw": "{{base_url}}/api/auth/teacher-login/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "auth", "teacher-login", ""]
                        }
                    }
                }
            ]
        },
        {
            "name": "Bulk Payments",
            "item": [
                {
                    "name": "1. Create Bulk Payments",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{access_token}}"},
                            {"key": "Content-Type", "value": "application/json"}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "student_ids": [
                                    "ENTER_STUDENT_UUID_1",
                                    "ENTER_STUDENT_UUID_2"
                                ],
                                "group_id": None,
                                "payment_type": "monthly",
                                "amount": "150.00",
                                "session_count": 8,
                                "due_date": "2026-03-01",
                                "notes": "Bulk payment for March"
                            }, indent=4)
                        },
                        "url": {
                            "raw": "{{base_url}}/api/payments/bulk_create/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "payments", "bulk_create", ""]
                        }
                    }
                },
                {
                    "name": "2. Perform Bulk Action (e.g. Mark Paid)",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{access_token}}"},
                            {"key": "Content-Type", "value": "application/json"}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "payment_ids": [
                                    "ENTER_PAYMENT_UUID_1",
                                    "ENTER_PAYMENT_UUID_2"
                                ],
                                "action": "mark_paid",
                                "payment_method": "cash",
                                "notes": "Paid in cash together"
                            }, indent=4)
                        },
                        "url": {
                            "raw": "{{base_url}}/api/payments/bulk_action/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "payments", "bulk_action", ""]
                        }
                    }
                }
            ]
        },
        {
            "name": "Admin Dashboard",
            "item": [
                {
                    "name": "1. List All Teachers",
                    "request": {
                        "method": "GET",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{admin_access_token}}"}
                        ],
                        "url": {
                            "raw": "{{base_url}}/api/admin/teachers/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "admin", "teachers", ""]
                        }
                    }
                },
                {
                    "name": "2. Suspend Teacher",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{admin_access_token}}"}
                        ],
                        "url": {
                            "raw": "{{base_url}}/api/admin/teachers/{{teacher_id}}/suspend/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "admin", "teachers", "{{teacher_id}}", "suspend"]
                        }
                    }
                },
                {
                    "name": "3. Activate Teacher",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{admin_access_token}}"}
                        ],
                        "url": {
                            "raw": "{{base_url}}/api/admin/teachers/{{teacher_id}}/activate/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "admin", "teachers", "{{teacher_id}}", "activate"]
                        }
                    }
                },
                {
                    "name": "4. Update Teacher Subscription",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{admin_access_token}}"},
                            {"key": "Content-Type", "value": "application/json"}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "plan": "premium",
                                "days": 365
                            }, indent=4)
                        },
                        "url": {
                            "raw": "{{base_url}}/api/admin/teachers/{{teacher_id}}/update_subscription/",
                            "host": ["{{base_url}}"],
                            "path": ["api", "admin", "teachers", "{{teacher_id}}", "update_subscription"]
                        }
                    }
                }
            ]
        }
    ],
    "variable": [
        {
            "key": "base_url",
            "value": "http://127.0.0.1:8000"
        },
        {
            "key": "access_token",
            "value": ""
        },
        {
            "key": "admin_access_token",
            "value": "ENTER_ADMIN_TOKEN_HERE"
        },
        {
            "key": "teacher_id",
            "value": "ENTER_TEACHER_UUID_HERE"
        }
    ]
}

with open("Teacher_Auth_BulkPayments.postman_collection.json", "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print("Successfully created Teacher_Auth_BulkPayments.postman_collection.json")
