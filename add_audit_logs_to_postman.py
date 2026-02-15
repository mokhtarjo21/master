"""
Script to add Audit Logs APIs to Postman Collection
"""
import json

# Load Postman collection
with open('smart_teacher_assistant_full.postman_collection.json', 'r', encoding='utf-8') as f:
    collection = json.load(f)

# Create Audit Logs section
audit_logs_section = {
    "name": "Audit Logs & Activity Tracking",
    "item": [
        {
            "name": "List Audit Logs",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/audit/logs/?action=create&model_name=Student",
                    "host": ["{{base_url}}"],
                    "path": ["audit", "logs", ""],
                    "query": [
                        {"key": "action", "value": "create", "disabled": True},
                        {"key": "model_name", "value": "Student", "disabled": True}
                    ]
                },
                "description": "Get all audit logs with optional filters"
            },
            "response": []
        },
        {
            "name": "Get Audit Log Details",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/audit/logs/{{log_id}}/",
                    "host": ["{{base_url}}"],
                    "path": ["audit", "logs", "{{log_id}}", ""]
                },
                "description": "Get specific audit log details"
            },
            "response": []
        },
        {
            "name": "Activity Summary",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/audit/logs/activity_summary/?start_date=2026-02-01&end_date=2026-02-28",
                    "host": ["{{base_url}}"],
                    "path": ["audit", "logs", "activity_summary", ""],
                    "query": [
                        {"key": "start_date", "value": "2026-02-01"},
                        {"key": "end_date", "value": "2026-02-28"}
                    ]
                },
                "description": "Get activity summary with aggregations"
            },
            "response": []
        },
        {
            "name": "Search Logs",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/audit/logs/?search=أحمد",
                    "host": ["{{base_url}}"],
                    "path": ["audit", "logs", ""],
                    "query": [
                        {"key": "search", "value": "أحمد"}
                    ]
                },
                "description": "Search logs by object name or username"
            },
            "response": []
        }
    ]
}

# Add to collection
collection['item'].append(audit_logs_section)

# Save updated collection
with open('smart_teacher_assistant_full.postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(collection, f, ensure_ascii=False, indent=2)

print(f"[SUCCESS] Added Audit Logs & Activity Tracking section to Postman collection")
print(f"Total sections now: {len(collection['item'])}")
print(f"Audit Logs APIs added: 4 endpoints")
