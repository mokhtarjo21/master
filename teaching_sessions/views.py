"""
Session Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import Session, SessionReminder, SessionMaterial, SessionNote
from .serializers import (
    SessionSerializer, SessionCreateSerializer, SessionListSerializer,
    SessionDetailSerializer, SessionReminderSerializer, SessionMaterialSerializer,
    SessionNoteSerializer, SessionScheduleSerializer
)


class SessionViewSet(viewsets.ModelViewSet):
    """Session management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'group', 'date']
    search_fields = ['title', 'description', 'group__name']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['date', 'start_time']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Session.objects.filter(group__teacher=self.request.user, is_active=True)
        elif self.request.user.user_type in ['student', 'parent']:
            # Students and parents can see sessions for their groups
            if self.request.user.user_type == 'student':
                from students.models import StudentGroup
                group_ids = StudentGroup.objects.filter(
                    student__user=self.request.user,
                    is_active=True
                ).values_list('group_id', flat=True)
            else:  # parent
                from students.models import StudentParentLink, StudentGroup
                linked_student_ids = StudentParentLink.objects.filter(
                    parent__user=self.request.user,
                    is_active=True
                ).values_list('student_id', flat=True)
                
                group_ids = StudentGroup.objects.filter(
                    student_id__in=linked_student_ids,
                    is_active=True
                ).values_list('group_id', flat=True)
            
            return Session.objects.filter(group_id__in=group_ids, is_active=True)
        
        return Session.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SessionCreateSerializer
        elif self.action == 'list':
            return SessionListSerializer
        elif self.action == 'retrieve':
            return SessionDetailSerializer
        return SessionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new session"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create sessions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            session = serializer.save()
            response_serializer = SessionSerializer(session)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        """Start a session"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can start sessions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        session = self.get_object()
        if session.status != 'scheduled':
            return Response(
                {'error': 'Session must be scheduled to start'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.start_session()
        serializer = SessionSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End a session"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can end sessions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        session = self.get_object()
        if session.status != 'in_progress':
            return Response(
                {'error': 'Session must be in progress to end'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.end_session()
        serializer = SessionSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel_session(self, request, pk=None):
        """Cancel a session"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can cancel sessions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        session = self.get_object()
        reason = request.data.get('reason', '')
        
        session.cancel_session(reason)
        serializer = SessionSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def attendance(self, request, pk=None):
        """Get session attendance"""
        session = self.get_object()
        
        from attendance.models import Attendance
        from attendance.serializers import AttendanceSerializer
        
        attendance_qs = Attendance.objects.filter(session=session).select_related('student')
        serializer = AttendanceSerializer(attendance_qs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def take_attendance(self, request, pk=None):
        """Take attendance for session"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can take attendance'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        session = self.get_object()
        if not session.can_take_attendance():
            return Response(
                {'error': 'Cannot take attendance for this session'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attendance_data = request.data.get('attendance', [])
        
        from attendance.models import Attendance
        created_count = 0
        updated_count = 0
        
        for item in attendance_data:
            student_id = item.get('student_id')
            status_value = item.get('status', 'present')
            notes = item.get('notes', '')
            
            if not student_id:
                continue
            
            attendance, created = Attendance.objects.update_or_create(
                session=session,
                student_id=student_id,
                defaults={
                    'status': status_value,
                    'notes': notes,
                    'marked_at': timezone.now()
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        # Update session attendance summary
        session.update_attendance_summary()
        
        return Response({
            'message': f'Attendance recorded: {created_count} new, {updated_count} updated',
            'created': created_count,
            'updated': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def schedule(self, request):
        """Get session schedule"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date:
            start_date = timezone.now().date()
        else:
            start_date = date.fromisoformat(start_date)
        
        if not end_date:
            end_date = start_date + timedelta(days=7)
        else:
            end_date = date.fromisoformat(end_date)
        
        queryset = self.get_queryset().filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('group')
        
        # Group sessions by date
        schedule_data = {}
        for session in queryset:
            date_str = session.date.isoformat()
            if date_str not in schedule_data:
                schedule_data[date_str] = {
                    'date': session.date,
                    'sessions': [],
                    'total_sessions': 0,
                    'completed_sessions': 0,
                    'cancelled_sessions': 0
                }
            
            schedule_data[date_str]['sessions'].append(session)
            schedule_data[date_str]['total_sessions'] += 1
            
            if session.status == 'completed':
                schedule_data[date_str]['completed_sessions'] += 1
            elif session.status == 'cancelled':
                schedule_data[date_str]['cancelled_sessions'] += 1
        
        # Convert to list and serialize
        schedule_list = []
        for date_str in sorted(schedule_data.keys()):
            day_data = schedule_data[date_str]
            day_data['sessions'] = SessionListSerializer(day_data['sessions'], many=True).data
            schedule_list.append(day_data)
        
        return Response(schedule_list)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's sessions"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(date=today).select_related('group')
        serializer = SessionListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming sessions"""
        today = timezone.now().date()
        days = int(request.query_params.get('days', 7))
        end_date = today + timedelta(days=days)
        
        queryset = self.get_queryset().filter(
            date__gte=today,
            date__lte=end_date,
            status='scheduled'
        ).select_related('group')
        
        serializer = SessionListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get session statistics"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view statistics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        stats = queryset.aggregate(
            total=Count('id'),
            scheduled=Count('id', filter=Q(status='scheduled')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            in_progress=Count('id', filter=Q(status='in_progress'))
        )
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def weekly_schedule(self, request):
        """
        Full weekly calendar view grouped by Arabic day name.

        Query params:
          week_start  — YYYY-MM-DD (auto-snaps to Monday of that week)
                        defaults to current week's Monday
          group_id    — filter to a specific group
        """
        from groups.models import GroupSchedule
        from django.db.models import Count, Q

        ARABIC_DAYS = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس',
                       'الجمعة', 'السبت', 'الأحد']

        # ── Week range ────────────────────────────────────────────────────────
        week_start_str = request.query_params.get('week_start')
        if week_start_str:
            try:
                week_start = date.fromisoformat(week_start_str)
                week_start = week_start - timedelta(days=week_start.weekday())
            except ValueError:
                return Response({'error': 'Invalid week_start. Use YYYY-MM-DD.'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            today_date = timezone.now().date()
            week_start = today_date - timedelta(days=today_date.weekday())

        week_end = week_start + timedelta(days=6)
        today_date = timezone.now().date()

        # ── Sessions ──────────────────────────────────────────────────────────
        qs = self.get_queryset().filter(
            date__gte=week_start, date__lte=week_end,
        ).select_related('group').annotate(
            attended_count=Count(
                'attendance_records',
                filter=Q(attendance_records__status='present')
            )
        )
        group_id = request.query_params.get('group_id')
        if group_id:
            qs = qs.filter(group_id=group_id)

        sessions_by_date = {}
        for s in qs:
            sessions_by_date.setdefault(s.date.isoformat(), []).append(s)

        # ── Fixed group schedules ─────────────────────────────────────────────
        fixed_qs = GroupSchedule.objects.filter(
            group__teacher=request.user, is_active=True
        ).select_related('group')
        if group_id:
            fixed_qs = fixed_qs.filter(group_id=group_id)

        fixed_by_weekday = {}
        for fs in fixed_qs:
            fixed_by_weekday.setdefault(fs.weekday, []).append(fs)

        # ── Build days ────────────────────────────────────────────────────────
        days = []
        summary = {'total_sessions': 0, 'completed': 0,
                   'scheduled': 0, 'cancelled': 0, 'in_progress': 0}

        for i in range(7):
            day_date = week_start + timedelta(days=i)
            weekday  = day_date.weekday()
            date_key = day_date.isoformat()
            day_sessions = sorted(
                sessions_by_date.get(date_key, []),
                key=lambda x: x.start_time
            )

            sessions_data = []
            for s in day_sessions:
                summary['total_sessions'] += 1
                summary[s.status] = summary.get(s.status, 0) + 1
                sessions_data.append({
                    'id':             str(s.id),
                    'title':          s.title,
                    'group_name':     s.group.name,
                    'group_id':       str(s.group.id),
                    'group_type':     s.group.group_type,
                    'subject':        s.group.subject or '',
                    'start_time':     str(s.start_time),
                    'end_time':       str(s.end_time),
                    'status':         s.status,
                    'classroom':      s.group.classroom or '',
                    'online_link':    s.group.online_meeting_link or '',
                    'students_count': s.group.current_students_count,
                    'attended_count': s.attended_count,
                })

            # Fixed schedules not yet having a session this day
            session_group_ids = {s.group_id for s in day_sessions}
            fixed_data = [
                {
                    'group_name':  fs.group.name,
                    'group_id':    str(fs.group.id),
                    'start_time':  str(fs.start_time),
                    'end_time':    str(fs.end_time),
                    'has_session': fs.group_id in session_group_ids,
                }
                for fs in fixed_by_weekday.get(weekday, [])
            ]

            days.append({
                'date':            date_key,
                'day_name':        ARABIC_DAYS[weekday],
                'day_index':       weekday,
                'is_today':        day_date == today_date,
                'session_count':   len(sessions_data),
                'sessions':        sessions_data,
                'fixed_schedules': fixed_data,
            })

        return Response({
            'week_start': week_start.isoformat(),
            'week_end':   week_end.isoformat(),
            'days':       days,
            'summary':    summary,
        })

class SessionReminderViewSet(viewsets.ModelViewSet):
    """Session reminder management"""
    serializer_class = SessionReminderSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return SessionReminder.objects.filter(
            session__group__teacher=self.request.user
        ).select_related('session')


class SessionMaterialViewSet(viewsets.ModelViewSet):
    """Session material management"""
    serializer_class = SessionMaterialSerializer
    permission_classes = [ReadOnlyForStudentsAndParents]
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return SessionMaterial.objects.filter(
                session__group__teacher=self.request.user
            ).select_related('session')
        else:
            # Students and parents can view materials for their sessions
            session_ids = Session.objects.filter(
                id__in=self._get_accessible_session_ids()
            ).values_list('id', flat=True)
            
            return SessionMaterial.objects.filter(session_id__in=session_ids)
    
    def _get_accessible_session_ids(self):
        """Get session IDs accessible to current user"""
        if self.request.user.user_type == 'student':
            from students.models import StudentGroup
            group_ids = StudentGroup.objects.filter(
                student__user=self.request.user,
                is_active=True
            ).values_list('group_id', flat=True)
        else:  # parent
            from students.models import StudentParentLink, StudentGroup
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True
            ).values_list('student_id', flat=True)
            
            group_ids = StudentGroup.objects.filter(
                student_id__in=linked_student_ids,
                is_active=True
            ).values_list('group_id', flat=True)
        
        return Session.objects.filter(
            group_id__in=group_ids,
            is_active=True
        ).values_list('id', flat=True)


class SessionNoteViewSet(viewsets.ModelViewSet):
    """Session note management"""
    serializer_class = SessionNoteSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return SessionNote.objects.filter(
            session__group__teacher=self.request.user
        ).select_related('session')