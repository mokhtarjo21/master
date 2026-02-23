import json

d = json.load(open('Smart_Teacher_Assistant.postman_collection.json', encoding='utf-8'))

total_with_filters = 0
print("=== Requests with Query Filters ===\n")
for folder in d['item']:
    for req in folder.get('item', []):
        params = req.get('request', {}).get('url', {}).get('query', [])
        if params:
            total_with_filters += 1
            print(f"[{folder['name']}] {req['name']}:")
            for p in params:
                status = "(disabled)" if p.get("disabled") else "(active)"
                print(f"    ? {p['key']} = {p['value']}  [{p.get('description','')}] {status}")
            print()

print(f"Total requests with filters: {total_with_filters}")
