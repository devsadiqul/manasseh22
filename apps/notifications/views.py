from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from .models import Notification
from .serializers import NotificationSerializer


# Create your views here.
@swagger_auto_schema(
    method="get",
    operation_summary="List notifications",
    operation_description="Returns all notifications split into 'new' (unread) and 'earlier' (read).",
    responses={200: NotificationSerializer(many=True)},
    tags=["Notifications"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user)
    unread_count = notifications.filter(is_read=False).count()
    return Response({
        "unread_count": unread_count,
        "new": NotificationSerializer(notifications.filter(is_read=False), many=True).data,
        "earlier": NotificationSerializer(notifications.filter(is_read=True), many=True).data,
    })


@swagger_auto_schema(
    method="post",
    operation_summary="Mark all notifications as read",
    responses={200: "All notifications marked as read."},
    tags=["Notifications"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def notification_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({"message": "All notifications marked as read."})


@swagger_auto_schema(
    method="patch",
    operation_summary="Mark a single notification as read",
    responses={200: NotificationSerializer},
    tags=["Notifications"],
    security=[{"Bearer": []}],
)
@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if notification.is_read:
        return Response({"detail": "Notification is already marked as read."})
    notification.is_read = True
    notification.save()
    return Response({
        "message": "Notification marked as read.",
        "notification": NotificationSerializer(notification).data,
    })