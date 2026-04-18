from django.urls import path
from . import views


# Create your urls here.
urlpatterns = [
    path("notifications/", views.notification_list, name="notification-list"),
    path("notifications/mark-all-read/", views.notification_mark_all_read, name="notification-mark-all-read"),
    path("notifications/<uuid:notification_id>/mark-read/", views.notification_mark_read, name="notification-mark-read"),
]