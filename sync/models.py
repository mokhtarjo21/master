"""
Sync Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SyncQueue(models.Model):
    """Queue for offline changes"""
    OPERATIONS = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_queue'
    )
    
    # Operation details
    operation = models.CharField(max_length=10, choices=OPERATIONS)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    data = models.JSONField(default=dict)
    
    # Sync status
    synced = models.BooleanField(default=False)
    sync_attempts = models.IntegerField(default=0)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'sync_queue'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['user', 'synced']),
            models.Index(fields=['model_name', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.operation} {self.model_name} - {self.synced}"


class SyncLog(models.Model):
    """Sync operation logs"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('conflict', 'Conflict'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sync_queue = models.ForeignKey(SyncQueue, on_delete=models.CASCADE, related_name='logs')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    synced_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sync_logs'
        ordering = ['-synced_at']
    
    def __str__(self):
        return f"{self.sync_queue.model_name} - {self.status}"


class SyncConflict(models.Model):
    """Track sync conflicts"""
    RESOLUTION_TYPES = [
        ('last_write_wins', 'Last Write Wins'),
        ('manual', 'Manual Resolution'),
        ('server_wins', 'Server Wins'),
        ('client_wins', 'Client Wins'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sync_queue = models.ForeignKey(SyncQueue, on_delete=models.CASCADE, related_name='conflicts')
    
    # Conflict data
    local_data = models.JSONField(default=dict)
    server_data = models.JSONField(default=dict)
    
    # Resolution
    resolution = models.CharField(max_length=20, choices=RESOLUTION_TYPES, default='last_write_wins')
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sync_conflicts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Conflict: {self.sync_queue.model_name} - {self.resolution}"
