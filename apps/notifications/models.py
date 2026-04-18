from django.db import models
from django.conf import settings
import uuid
from apps.tasks.models import Event, Task


# Create your models here.
class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ("task_completed", "Task Completed"),
        ("member_added", "Member Added"),
        ("task_comment", "Task Comment"),
        ("task_assigned", "Task Assigned"),
        ("premium_upsell", "Premium Upsell"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sent_notifications"
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_event = models.ForeignKey(
        Event, on_delete=models.SET_NULL, null=True, blank=True
    )
    related_task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.email}: {self.title}"