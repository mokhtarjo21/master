"""
Custom Permission Classes
"""
from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """Permission for teacher users only"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'teacher'


class IsStudent(permissions.BasePermission):
    """Permission for student users only"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'student'


class IsParent(permissions.BasePermission):
    """Permission for parent users only"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'parent'


class IsStudentOrParent(permissions.BasePermission):
    """Permission for student or parent users"""
    
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.user_type in ['student', 'parent'])


class IsTeacherOwner(permissions.BasePermission):
    """Permission for teacher who owns the resource"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or request.user.user_type != 'teacher':
            return False
        
        # Check if object has teacher field
        if hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        
        # Check if object is the teacher themselves
        if hasattr(obj, 'user_type') and obj.user_type == 'teacher':
            return obj == request.user
        
        return False


class ReadOnlyForStudentsAndParents(permissions.BasePermission):
    """Read-only permission for students and parents"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type == 'teacher':
            return True
        
        if request.user.user_type in ['student', 'parent']:
            return request.method in permissions.SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'teacher':
            if hasattr(obj, 'teacher'):
                return obj.teacher == request.user
            elif hasattr(obj, 'group') and hasattr(obj.group, 'teacher'):
                return obj.group.teacher == request.user
            # Check Session related
            elif hasattr(obj, 'session') and hasattr(obj.session, 'group') and hasattr(obj.session.group, 'teacher'):
                return obj.session.group.teacher == request.user
            
            # Check Student related (Payment, Receipt, etc)
            student = None
            if hasattr(obj, 'student'):
                student = obj.student
            elif hasattr(obj, 'payment') and hasattr(obj.payment, 'student'):
                student = obj.payment.student
            
            if student:
                # Check direct teacher assignment
                if hasattr(student, 'teacher') and student.teacher == request.user:
                    return True
                # Check group enrollment
                if hasattr(student, 'student_groups'):
                    return student.student_groups.filter(group__teacher=request.user, is_active=True).exists()
            
            return False
        
        if request.user.user_type in ['student', 'parent']:
            if request.method not in permissions.SAFE_METHODS:
                return False
            
            # Students can only view their own data
            if request.user.user_type == 'student':
                if hasattr(obj, 'student'):
                    return obj.student.user == request.user
                elif hasattr(obj, 'user'):
                    return obj.user == request.user
            
            # Parents can view their linked students' data
            elif request.user.user_type == 'parent':
                from students.models import StudentParentLink
                linked_students = StudentParentLink.objects.filter(
                    parent__user=request.user,
                    is_active=True
                ).values_list('student_id', flat=True)
                
                if hasattr(obj, 'student'):
                    return obj.student.id in linked_students
                elif hasattr(obj, 'id') and hasattr(obj, '_meta') and obj._meta.model_name == 'student':
                    return obj.id in linked_students
        
        return False