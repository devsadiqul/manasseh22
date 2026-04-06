from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from .models import Notification
from .serializers import NotificationSerializer


# Create your views here.
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List notifications",
        operation_description="Returns all notifications split into 'new' (unread) and 'earlier' (read).",
        responses={200: NotificationSerializer(many=True)},
        tags=["Notifications"],
        security=[{"Bearer": []}],
    )
    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        unread_count = notifications.filter(is_read=False).count()
        return Response({
            "unread_count": unread_count,
            "new": NotificationSerializer(notifications.filter(is_read=False), many=True).data,
            "earlier": NotificationSerializer(notifications.filter(is_read=True), many=True).data,
        })


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Mark all notifications as read",
        responses={200: "All notifications marked as read."},
        tags=["Notifications"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Mark a single notification as read",
        responses={200: NotificationSerializer},
        tags=["Notifications"],
        security=[{"Bearer": []}],
    )
    def patch(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)