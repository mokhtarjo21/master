"""
Sync Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import SyncQueue, SyncLog, SyncConflict
from .serializers import SyncChangeSerializer, SyncStatusSerializer, SyncConflictSerializer


class SyncViewSet(viewsets.ViewSet):
    """Sync management viewset"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get sync status"""
        pending = SyncQueue.objects.filter(user=request.user, synced=False).count()
        conflicts = SyncConflict.objects.filter(
            sync_queue__user=request.user,
            resolved=False
        ).count()
        
        last_sync = SyncQueue.objects.filter(
            user=request.user,
            synced=True
        ).order_by('-synced_at').first()
        
        return Response({
            'last_sync': last_sync.synced_at if last_sync else None,
            'sync_status': 'completed' if pending == 0 else 'pending',
            'pending_changes': pending,
            'conflicts': conflicts,
            'next_sync': None
        })
    
    @action(detail=False, methods=['post'])
    def push(self, request):
        """Push local changes to server"""
        serializer = SyncChangeSerializer(data=request.data.get('changes', []), many=True)
        serializer.is_valid(raise_exception=True)
        
        processed = 0
        conflicts = 0
        errors = 0
        results = []
        
        for change in serializer.validated_data:
            try:
                # Create sync queue entry
                sync_item = SyncQueue.objects.create(
                    user=request.user,
                    operation=change['action'],
                    model_name=change['model'],
                    object_id=change['id'],
                    data=change['data']
                )
                
                # TODO: Process the sync item (apply changes to database)
                # For now, just mark as synced
                sync_item.synced = True
                sync_item.synced_at = timezone.now()
                sync_item.save()
                
                SyncLog.objects.create(
                    sync_queue=sync_item,
                    status='success'
                )
                
                processed += 1
                results.append({
                    'local_id': change['id'],
                    'server_id': change['id'],
                    'status': change['action'] + 'd'
                })
                
            except Exception as e:
                errors += 1
                results.append({
                    'local_id': change['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return Response({
            'processed': processed,
            'conflicts': conflicts,
            'errors': errors,
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def pull(self, request):
        """Pull server changes"""
        since = request.query_params.get('since')
        
        # TODO: Get changes from server since timestamp
        # For now, return empty changes
        
        return Response({
            'changes': [],
            'has_more': False,
            'next_cursor': None
        })
    
    @action(detail=False, methods=['post'])
    def resolve_conflicts(self, request):
        """Resolve sync conflicts"""
        resolutions = request.data.get('resolutions', [])
        
        for resolution in resolutions:
            conflict_id = resolution.get('conflict_id')
            resolution_type = resolution.get('resolution', 'server_wins')
            
            try:
                conflict = SyncConflict.objects.get(
                    id=conflict_id,
                    sync_queue__user=request.user
                )
                
                conflict.resolution = resolution_type
                conflict.resolved = True
                conflict.resolved_at = timezone.now()
                conflict.save()
                
            except SyncConflict.DoesNotExist:
                pass
        
        return Response({
            'message': 'Conflicts resolved',
            'resolved_count': len(resolutions)
        })
