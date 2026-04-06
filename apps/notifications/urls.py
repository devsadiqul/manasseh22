from django.urls import path
from . import views


# Create your urls here.
urlpatterns = [
    path("notifications/", views.NotificationListView.as_view(), name="notifications"),
    path("notifications/read-all/", views.MarkAllNotificationsReadView.as_view(), name="notifications-read-all"),
    path("notifications/<uuid:notification_id>/read/", views.MarkNotificationReadView.as_view(), name="notification-read"),
]