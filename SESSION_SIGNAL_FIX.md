# Session Signal Fix

## Problem

When creating a new session via `POST /api/sessions/`, the following error occurred:

```
AttributeError: 'Session' object has no attribute 'session_date'
File: rules_engine/signals.py, line 249
```

## Root Cause

The `trigger_session_rules` signal handler in `rules_engine/signals.py` was using incorrect field names that don't match the actual `Session` model:

**Incorrect:**
```python
'session_date': str(instance.session_date),  # ❌ No such field
'duration': instance.duration,               # ❌ No such field
'topic': instance.topic or '',               # ❌ No such field
```

**Session Model Fields (teaching_sessions/models.py):**
```python
class Session(models.Model):
    date = models.DateField()              # ✅ Not session_date
    start_time = models.TimeField()        # ✅ Correct
    end_time = models.TimeField()          # ✅ Correct
    title = models.CharField(...)          # ✅ Not topic
    description = models.TextField(...)    # ✅ Available
    status = models.CharField(...)         # ✅ Available
    # No 'duration' field - calculated from start/end time
```

## Solution

Updated `rules_engine/signals.py` line 243-254 to use correct field names:

```python
# Build context
context = {
    'session_id': str(instance.id),
    'group': instance.group,
    'group_id': str(instance.group.id),
    'group_name': instance.group.name,
    'session_date': str(instance.date),           # ✅ Fixed: date not session_date
    'start_time': str(instance.start_time) if instance.start_time else None,
    'end_time': str(instance.end_time) if instance.end_time else None,
    'title': instance.title or '',                # ✅ Fixed: title not topic
    'description': instance.description or '',    # ✅ Added
    'status': instance.status,                    # ✅ Added
}
```

## Impact

- ✅ Session creation now works without errors
- ✅ Rules engine receives correct context data
- ✅ All session fields properly mapped

## Testing

```bash
POST /api/sessions/
{
  "group": "group-uuid",
  "date": "2026-02-17",
  "start_time": "10:00:00",
  "end_time": "12:00:00",
  "title": "Math Session"
}

Response: 201 Created ✅
```

## Files Changed

- `rules_engine/signals.py` (lines 243-254)
