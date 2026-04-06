from .models import Notification


def send_notification(recipient, sender, notification_type, title, message, related_group=None, related_task=None):
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        related_group=related_group,
        related_task=related_task,
    )