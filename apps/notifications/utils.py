from .models import Notification


# Create your utils here.
def send_notification(recipient, sender, notification_type, title, message, related_event=None, related_task=None):
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        related_event=related_event,
        related_task=related_task,
    )