"""
Sync Serializers
"""
from rest_framework import serializers
from .models import SyncQueue, SyncLog, SyncConflict


class SyncChangeSerializer(serializers.Serializer):
    """Sync change serializer"""
    id = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    action = serializers.ChoiceField(choices=['create', 'update', 'delete'])
    data = serializers.JSONField()
    timestamp = serializers.DateTimeField()


class SyncStatusSerializer(serializers.Serializer):
    """Sync status serializer"""
    last_sync = serializers.DateTimeField(allow_null=True)
    sync_status = serializers.CharField()
    pending_changes = serializers.IntegerField()
    conflicts = serializers.IntegerField()
    next_sync = serializers.DateTimeField(allow_null=True)


class SyncConflictSerializer(serializers.ModelSerializer):
    """Sync conflict serializer"""
    
    class Meta:
        model = SyncConflict
        fields = [
            'id', 'local_data', 'server_data', 'resolution',
            'resolved', 'resolved_at', 'created_at'
        ]
