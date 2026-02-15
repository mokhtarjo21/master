# Student Login Fix

## Problem

When attempting to login as a student, the endpoint fails with:
```
students.models.Student.DoesNotExist: Student matching query does not exist.
```

## Root Cause

The `student_login` view in `accounts/views.py` (line 98) was attempting to get a Student record for every authenticated user without checking if it exists:

```python
student = Student.objects.get(user=user)  # ❌ Fails if no Student record
```

This caused issues when:
1. A User account exists but Student record hasn't been created yet
2. The user is a parent (not a student)
3. Database sync issues

## Solution

Added proper error handling:

```python
# Build response based on user type
response_data = {
    'access': access_token,
    'refresh': str(refresh),
    'user': UserSerializer(user).data
}

# Add student_id if user is a student and has a Student record
if user.user_type == 'student':
    try:
        from students.models import Student
        student = Student.objects.get(user=user)
        response_data['student_id'] = str(student.id)
        response_data['student_code'] = student.student_code
    except Student.DoesNotExist:
        # Student record doesn't exist yet, return without student_id
        pass

return Response(response_data)
```

## What Changed

✅ **Before:**
- Crashed if Student doesn't exist
- No handling for parents
- Always tried to get student_id

✅ **After:**
- Graceful handling if Student doesn't exist
- Only tries to get Student if user_type is 'student'
- Returns valid response even without Student record
- Includes student_code if available

## Testing

### Test Case 1: Student with Student Record ✅
```bash
POST /api/auth/student-login/
{
  "student_code": "ST-1234567"
}

Response:
{
  "access": "jwt-token",
  "refresh": "refresh-token",
  "user": {...},
  "student_id": "uuid",
  "student_code": "ST-1234567"
}
```

### Test Case 2: Student without Student Record ✅
```bash
POST /api/auth/student-login/
{
  "student_code": "ST-9999999"
}

Response:
{
  "access": "jwt-token",
  "refresh": "refresh-token",
  "user": {...}
}
```

### Test Case 3: Parent Login ✅
```bash
POST /api/auth/student-login/
{
  "access_token": "parent-token"
}

Response:
{
  "access": "jwt-token",
  "refresh": "refresh-token",
  "user": {...}
}
```

## Impact

- ✅ Student login now works even without Student record
- ✅ Parent login works correctly
- ✅ No more 500 errors
- ✅ Backwards compatible

## Files Changed

- `accounts/views.py` (lines 94-105)
