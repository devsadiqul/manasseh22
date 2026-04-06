from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Notification


# Create your serializers here.
class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "sender", "notification_type", "title", "message",
            "related_group", "related_task", "is_read", "created_at",
        ]
        read_only_fields = fields