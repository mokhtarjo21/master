import json

# Read the existing collection
with open('smart_teacher_assistant_full.postman_collection.json', 'r', encoding='utf-8') as f:
    collection = json.load(f)

# New Settings API endpoints
settings_apis = {
    "name": "Settings & Security",
    "item": [
        {
            "name": "Get Settings",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/settings/",
                    "host": ["{{base_url}}"],
                    "path": ["settings", ""]
                },
                "description": "Get current teacher settings"
            },
            "response": []
        },
        {
            "name": "Update Settings",
            "request": {
                "method": "PUT",
                "header": [
                    {"key": "Content-Type", "value": "application/json", "type": "text"},
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/settings/{{settings_id}}/",
                    "host": ["{{base_url}}"],
                    "path": ["settings", "{{settings_id}}", ""]
                },
                "description": "Update teacher settings",
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"center_name\": \"مركز التعليم الذكي\",\n    \"language\": \"ar\",\n    \"theme\":  \"dark\",\n    \"whatsapp_enabled\": true,\n    \"two_factor_enabled\": false,\n    \"session_timeout_minutes\": 120,\n    \"default_session_duration\": 90\n}",
                    "options": {"raw": {"language": "json"}}
                }
            },
            "response": []
        },
        {
            "name": "Change PIN",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json", "type": "text"},
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/settings/change_pin/",
                    "host": ["{{base_url}}"],
                    "path": ["settings", "change_pin", ""]
                },
                "description": "Change teacher PIN (requires old PIN verification)",
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"old_pin\": \"1234\",\n    \"new_pin\": \"5678\",\n    \"confirm_pin\": \"5678\"\n}",
                    "options": {"raw": {"language": "json"}}
                }
            },
            "response": []
        },
        {
            "name": "Export Data",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/settings/export_data/",
                    "host": ["{{base_url}}"],
                    "path": ["settings", "export_data", ""]
                },
                "description": "Export all teacher data as JSON file"
            },
            "response": []
        },
        {
            "name": "Reset Data (Danger Zone)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json", "type": "text"},
                    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"}
                ],
                "url": {
                    "raw": "{{base_url}}/settings/reset_data/",
                    "host": ["{{base_url}}"],
                    "path": ["settings", "reset_data", ""]
                },
                "description": "DANGER: Delete data (requires exact confirmation text)",
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"reset_type\": \"delete_students\",\n    \"confirmation_text\": \"DELETE ALL STUDENTS\"\n}",
                    "options": {"raw": {"language": "json"}}
                }
            },
            "response": []
        }
    ]
}

# Add Settings section to collection
collection['item'].append(settings_apis)

# Save updated collection
with open('smart_teacher_assistant_full.postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(collection, f, ensure_ascii=False, indent=4)

print("[SUCCESS] Added Settings & Security section to Postman collection")
print(f"Total sections now: {len(collection['item'])}")
print(f"Settings APIs added: {len(settings_apis['item'])}")
