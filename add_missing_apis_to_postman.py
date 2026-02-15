"""
Add Missing APIs to Postman Collection
Adds ~33 missing endpoints to reach 100% coverage
"""
import json
import uuid

def load_collection(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_collection(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_request(name, method, path, description="", body=None):
    """Create a Postman request object"""
    request = {
        "name": name,
        "request": {
            "method": method,
            "header": [
                {
                    "key": "Authorization",
                    "value": "Bearer {{access_token}}",
                    "type": "text"
                },
                {
                    "key": "Content-Type",
                    "value": "application/json",
                    "type": "text"
                }
            ],
            "url": {
                "raw": f"{{{{base_url}}}}{path}",
                "host": ["{{base_url}}"],
                "path": path.strip('/').split('/')
            }
        },
        "response": []
    }
    
    if description:
        request["request"]["description"] = description
    
    if body and method in ['POST', 'PUT', 'PATCH']:
        request["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2, ensure_ascii=False)
        }
    
    return request

def find_section(collection, section_name):
    """Find a section by name"""
    for item in collection.get('item', []):
        if item.get('name') == section_name:
            return item
    return None

def add_missing_payments_apis(collection):
    """Add missing Payments APIs"""
    print("\n1. Adding Payments APIs...")
    
    # Find Payments section (might be under Financials)
    financials = find_section(collection, 'Financials')
    if not financials:
        financials = {
            "name": "Financials",
            "item": []
        }
        collection['item'].append(financials)
    
    # Find or create Payments subsection
    payments = None
    for item in financials.get('item', []):
        if item.get('name') == 'Payments':
            payments = item
            break
    
    if not payments:
        payments = {"name": "Payments", "item": []}
        financials['item'].append(payments)
    
    new_requests = [
        create_request(
            "Add Payment to Existing",
            "POST",
            "/api/payments/{payment_id}/add_payment/",
            "Add partial payment to existing payment record",
            {
                "amount": 500.00,
                "payment_method": "cash",
                "notes": "Partial payment",
                "transaction_reference": "TXN-123"
            }
        ),
        create_request(
            "Apply Discount",
            "POST",
            "/api/payments/{payment_id}/apply_discount/",
            "Apply discount to a payment",
            {
                "discount_amount": 100.00,
                "reason": "Early payment discount"
            }
        ),
        create_request(
            "Get Overdue Payments",
            "GET",
            "/api/payments/overdue/",
            "Get all overdue payments"
        ),
        create_request(
            "Get Due Soon Payments",
            "GET",
            "/api/payments/due_soon/",
            "Get payments due in next 7 days"
        ),
        create_request(
            "Get Payment Summary",
            "GET",
            "/api/payments/summary/",
            "Get payment statistics and summary"
        ),
        create_request(
            "Bulk Action on Payments",
            "POST",
            "/api/payments/bulk_action/",
            "Perform bulk actions on multiple payments",
            {
                "payment_ids": ["uuid1", "uuid2"],
                "action": "mark_paid",
                "payment_method": "cash"
            }
        ),
        create_request(
            "Monthly Report",
            "GET",
            "/api/payments/monthly_report/?month=3&year=2026",
            "Get monthly payment report"
        ),
        create_request(
            "Generate Monthly Payments",
            "POST",
            "/api/payments/generate_monthly_payments/",
            "Auto-generate monthly payments for all students",
            {
                "month": 3,
                "year": 2026
            }
        )
    ]
    
    payments['item'].extend(new_requests)
    print(f"   Added {len(new_requests)} Payments requests")

def add_missing_attendance_apis(collection):
    """Add missing Attendance APIs"""
    print("\n2. Adding Attendance APIs...")
    
    attendance = find_section(collection, 'Attendance')
    if not attendance:
        attendance = {"name": "Attendance", "item": []}
        collection['item'].append(attendance)
    
    new_requests = [
        create_request(
            "Bulk Create Attendance",
            "POST",
            "/api/attendance/bulk_create/",
            "Create attendance records for multiple students",
            {
                "session_id": "session-uuid",
                "attendance_records": [
                    {"student_id": "student1-uuid", "status": "present"},
                    {"student_id": "student2-uuid", "status": "absent"}
                ]
            }
        ),
        create_request(
            "Scan QR Code",
            "POST",
            "/api/attendance/scan_qr/",
            "Mark attendance by scanning student QR code",
            {
                "qr_code": "ST-1234567",
                "session_id": "session-uuid"
            }
        ),
        create_request(
            "Get Attendance Summary",
            "GET",
            "/api/attendance/summary/?student={student_id}",
            "Get attendance summary statistics"
        ),
        create_request(
            "Get Today's Attendance",
            "GET",
            "/api/attendance/today/",
            "Get attendance for today's sessions"
        )
    ]
    
    attendance['item'].extend(new_requests)
    print(f"   Added {len(new_requests)} Attendance requests")

def add_missing_grades_apis(collection):
    """Add missing Grades APIs"""
    print("\n3. Adding Grades APIs...")
    
    grades = find_section(collection, 'Grades')
    if not grades:
        grades = {"name": "Grades", "item": []}
        collection['item'].append(grades)
    
    new_requests = [
        create_request(
            "Update Grade",
            "PUT",
            "/api/grades/{grade_id}/",
            "Update a grade record",
            {
                "score_obtained": 95,
                "total_score": 100,
                "notes": "Excellent work"
            }
        ),
        create_request(
            "Delete Grade",
            "DELETE",
            "/api/grades/{grade_id}/",
            "Delete a grade record"
        ),
        create_request(
            "Get Student Grades",
            "GET",
            "/api/grades/student/{student_id}/",
            "Get all grades for a specific student"
        ),
        create_request(
            "Get Grade Statistics",
            "GET",
            "/api/grades/stats/?student={student_id}",
            "Get grade statistics and averages"
        ),
        create_request(
            "Bulk Create Grades",
            "POST",
            "/api/grades/bulk_create/",
            "Create grades for multiple students",
            {
                "grades": [
                    {
                        "student_id": "student1-uuid",
                        "grade_type": "homework",
                        "score_obtained": 90,
                        "total_score": 100
                    }
                ]
            }
        )
    ]
    
    grades['item'].extend(new_requests)
    print(f"   Added {len(new_requests)} Grades requests")

def add_missing_notifications_apis(collection):
    """Add missing Notifications APIs"""
    print("\n4. Adding Notifications APIs...")
    
    notifications = find_section(collection, 'Notifications')
    if not notifications:
        notifications = {"name": "Notifications", "item": []}
        collection['item'].append(notifications)
    
    new_requests = [
        create_request(
            "Bulk Create Notifications",
            "POST",
            "/api/notifications/bulk_create/",
            "Create notifications for multiple recipients",
            {
                "notification_type": "payment_reminder",
                "recipients": ["parent1-uuid", "parent2-uuid"],
                "title": "Payment Reminder",
                "message": "Please pay outstanding fees"
            }
        ),
        create_request(
            "Send WhatsApp",
            "POST",
            "/api/notifications/send_whatsapp/",
            "Send notification via WhatsApp",
            {
                "notification_id": "notification-uuid"
            }
        ),
        create_request(
            "Get Pending Notifications",
            "GET",
            "/api/notifications/pending/",
            "Get all pending (unsent) notifications"
        ),
        create_request(
            "Get Sent Notifications",
            "GET",
            "/api/notifications/sent/",
            "Get all sent notifications"
        )
    ]
    
    notifications['item'].extend(new_requests)
    print(f"   Added {len(new_requests)} Notifications requests")

def add_missing_receipts_apis(collection):
    """Add missing Receipts APIs"""
    print("\n5. Adding Receipts APIs...")
    
    # Find Receipts under Financials
    financials = find_section(collection, 'Financials')
    if not financials:
        financials = {"name": "Financials", "item": []}
        collection['item'].append(financials)
    
    receipts = None
    for item in financials.get('item', []):
        if item.get('name') == 'Receipts':
            receipts = item
            break
    
    if not receipts:
        receipts = {"name": "Receipts", "item": []}
        financials['item'].append(receipts)
    
    new_requests = [
        create_request(
            "Get Receipt Statistics",
            "GET",
            "/api/receipts/stats/",
            "Get receipt generation statistics"
        ),
        create_request(
            "Bulk Generate Receipts",
            "POST",
            "/api/receipts/bulk_generate/",
            "Generate receipts for multiple payments",
            {
                "payment_ids": ["payment1-uuid", "payment2-uuid"]
            }
        ),
        create_request(
            "Regenerate Receipt PDF",
            "POST",
            "/api/receipts/{receipt_id}/regenerate/",
            "Regenerate PDF for a receipt"
        )
    ]
    
    receipts['item'].extend(new_requests)
    print(f"   Added {len(new_requests)} Receipts requests")

def add_danger_zone_apis(collection):
    """Add Danger Zone APIs"""
    print("\n6. Adding Danger Zone APIs...")
    
    settings = find_section(collection, 'Settings & Security')
    if not settings:
        settings = {"name": "Settings & Security", "item": []}
        collection['item'].append(settings)
    
    # Create Danger Zone subsection
    danger_zone = {"name": "Danger Zone", "item": []}
    
    requests = [
        create_request(
            "Delete All Students",
            "DELETE",
            "/api/settings/danger-zone/students/",
            "⚠️ DANGER: Delete all student records",
            {"confirmation": "delete"}
        ),
        create_request(
            "Delete All Payments",
            "DELETE",
            "/api/settings/danger-zone/payments/",
            "⚠️ DANGER: Delete all payment records",
            {"confirmation": "delete"}
        ),
        create_request(
            "Delete All Grades",
            "DELETE",
            "/api/settings/danger-zone/grades/",
            "⚠️ DANGER: Delete all grade records",
            {"confirmation": "delete"}
        ),
        create_request(
            "Delete All Sessions",
            "DELETE",
            "/api/settings/danger-zone/sessions/",
            "⚠️ DANGER: Delete all session records",
            {"confirmation": "delete"}
        ),
        create_request(
            "Delete All Attendance",
            "DELETE",
            "/api/settings/danger-zone/attendance/",
            "⚠️ DANGER: Delete all attendance records",
            {"confirmation": "delete"}
        ),
        create_request(
            "Delete All Receipts",
            "DELETE",
            "/api/settings/danger-zone/receipts/",
            "⚠️ DANGER: Delete all receipt records",
            {"confirmation": "delete"}
        ),
        create_request(
            "Reset All Data",
            "DELETE",
            "/api/settings/danger-zone/reset-all/",
            "⚠️⚠️⚠️ EXTREME DANGER: Delete ALL data",
            {"confirmation": "delete"}
        )
    ]
    
    danger_zone['item'] = requests
    settings['item'].append(danger_zone)
    print(f"   Added {len(requests)} Danger Zone requests")

def add_sync_apis(collection):
    """Add Sync APIs"""
    print("\n7. Adding Sync APIs...")
    
    sync = find_section(collection, 'Sync')
    if not sync:
        sync = {"name": "Sync", "item": []}
        collection['item'].append(sync)
    
    new_requests = [
        create_request(
            "Get Sync Status",
            "GET",
            "/api/sync/status/",
            "Get current synchronization status"
        ),
        create_request(
            "Get Sync Conflicts",
            "GET",
            "/api/sync/conflicts/",
            "Get unresolved sync conflicts"
        ),
        create_request(
            "Resolve Sync Conflict",
            "POST",
            "/api/sync/resolve_conflict/",
            "Resolve a synchronization conflict",
            {
                "conflict_id": "conflict-uuid",
                "resolution": "use_server"
            }
        )
    ]
    
    sync['item'].extend(new_requests)
    print(f"   Added {len(new_requests)} Sync requests")

def main():
    filename = 'smart_teacher_assistant_full.postman_collection.json'
    
    print("=" * 80)
    print("ADDING MISSING APIS TO POSTMAN COLLECTION")
    print("=" * 80)
    
    # Load collection
    print(f"\nLoading {filename}...")
    collection = load_collection(filename)
    
    initial_count = sum(len(section.get('item', [])) for section in collection.get('item', []))
    print(f"Initial request count: {initial_count}")
    
    # Add missing APIs
    add_missing_payments_apis(collection)
    add_missing_attendance_apis(collection)
    add_missing_grades_apis(collection)
    add_missing_notifications_apis(collection)
    add_missing_receipts_apis(collection)
    add_danger_zone_apis(collection)
    add_sync_apis(collection)
    
    # Save collection
    print(f"\nSaving updated collection...")
    save_collection(filename, collection)
    
    final_count = sum(len(section.get('item', [])) for section in collection.get('item', []))
    added_count = final_count - initial_count
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Initial requests:  {initial_count}")
    print(f"Added requests:    {added_count}")
    print(f"Final requests:    {final_count}")
    print(f"\nCollection updated successfully! ✅")
    print("=" * 80)

if __name__ == '__main__':
    main()
