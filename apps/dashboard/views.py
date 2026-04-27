from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from apps.notifications.models import Notification
from apps.subscriptions.models import Subscription
from apps.tasks.models import Event, Task
from .serializers import (
    BroadcastNotificationSerializer,
    BroadcastSendSerializer,
    DashboardOverviewSerializer,
    DashboardEventSerializer,
    DashboardUserSerializer,
    DashboardUserDetailSerializer,
    UserGrowthSerializer,
)

User = get_user_model()


# Create your views here.
@swagger_auto_schema(
    method="get",
    operation_summary="Dashboard overview",
    operation_description="Returns total users, active groups, total tasks, active subscriptions.",
    responses={200: DashboardOverviewSerializer},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_overview(request):
    data = {
        "total_users": User.objects.count(),
        "active_groups": Event.objects.filter(event_date__gte=timezone.now()).count(),
        "total_tasks": Task.objects.count(),
        "active_subscriptions": Subscription.objects.filter(plan="premium", is_active=True).count(),
    }
    return Response(DashboardOverviewSerializer(data).data)


@swagger_auto_schema(
    method="get",
    operation_summary="User growth chart",
    operation_description="Returns monthly user registration count for the last 6 months.",
    responses={200: UserGrowthSerializer(many=True)},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def user_growth(request):
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    data = (
        User.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    result = [
        {"month": item["month"].strftime("%b"), "count": item["count"]}
        for item in data
    ]
    return Response(UserGrowthSerializer(result, many=True).data)


@swagger_auto_schema(
    method="get",
    operation_summary="Subscription growth chart",
    operation_description="Returns monthly subscription count (free & premium) for the last 6 months.",
    responses={200: UserGrowthSerializer(many=True)},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def subscription_growth(request):
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    data = (
        Subscription.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month", "plan")
        .annotate(count=Count("id"))
        .order_by("month", "plan")
    )

    result = [
        {
            "month": item["month"].strftime("%b"),
            "plan": item["plan"],
            "count": item["count"],
        }
        for item in data
    ]
    return Response(UserGrowthSerializer(result, many=True).data)


@swagger_auto_schema(
    method="get",
    operation_summary="Events list",
    operation_description="Returns all events with member count, event date, created by. Supports search and pagination.",
    manual_parameters=[
        openapi.Parameter("search", openapi.IN_QUERY, description="Search by event name", type=openapi.TYPE_STRING),
        openapi.Parameter("page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
    ],
    responses={200: DashboardEventSerializer(many=True)},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_events(request):
    search = request.query_params.get("search", "").strip()
    events = (
        Event.objects
        .select_related("created_by")
        .annotate(member_count=Count("members"))
        .order_by("-created_at")
    )

    if search:
        events = events.filter(name__icontains=search)

    paginator = Paginator(events, 10)
    page = paginator.get_page(request.query_params.get("page", 1))

    return Response({
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
        "events": DashboardEventSerializer(page, many=True, context={"request": request}).data,
    })


@swagger_auto_schema(
    method="get",
    operation_summary="Event detail",
    operation_description="Admin views any event details with members and tasks.",
    responses={200: "Event detail", 404: "Not found"},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_event_detail(request, event_id):
    event = get_object_or_404(
        Event.objects
        .select_related("created_by")
        .prefetch_related("members__user", "tasks__assigned_to"),
        id=event_id
    )

    return Response({
        "id": str(event.id),
        "name": event.name,
        "description": event.description,
        "cover_image": request.build_absolute_uri(event.cover_image.url) if event.cover_image else None,
        "event_date": event.event_date,
        "days_left": event.days_left,
        "created_by": {
            "id": str(event.created_by.id),
            "name": event.created_by.name,
            "email": event.created_by.email,
        },
        "member_count": event.members.count(),
        "members": [
            {
                "id": str(m.user.id),
                "name": m.user.name,
                "email": m.user.email,
                "image": request.build_absolute_uri(m.user.image.url) if m.user.image else None,
                "role": m.role,
            }
            for m in event.members.all()
        ],
        "task_count": event.task_count,
        "completed_task_count": event.completed_task_count,
        "tasks": [
            {
                "id": str(t.id),
                "name": t.name,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "assigned_to": {
                    "id": str(t.assigned_to.id),
                    "name": t.assigned_to.name,
                } if t.assigned_to else None,
            }
            for t in event.tasks.all()
        ],
    })


@swagger_auto_schema(
    method="delete",
    operation_summary="Delete event",
    operation_description="Admin deletes any event.",
    responses={200: "Deleted", 404: "Not found"},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_event_delete(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    return Response({"message": "Event deleted successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="get",
    operation_summary="Users list",
    operation_description="Returns all users with groups count, subscription, status. Supports search and pagination.",
    manual_parameters=[
        openapi.Parameter("search", openapi.IN_QUERY, description="Search by name or email", type=openapi.TYPE_STRING),
        openapi.Parameter("page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
    ],
    responses={200: DashboardUserSerializer(many=True)},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_users(request):
    search = request.query_params.get("search", "").strip()
    users = (
        User.objects
        .select_related("subscription")
        .annotate(groups_count=Count("event_memberships"))
        .order_by("-created_at")
    )

    if search:
        users = users.filter(
            Q(name__icontains=search) | Q(email__icontains=search)
        )

    paginator = Paginator(users, 10)
    page = paginator.get_page(request.query_params.get("page", 1))

    return Response({
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
        "users": DashboardUserSerializer(page, many=True, context={"request": request}).data,
    })


@swagger_auto_schema(
    method="get",
    operation_summary="User detail",
    operation_description="Admin views any user's full details.",
    responses={200: DashboardUserDetailSerializer},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_user_detail(request, user_id):
    user = get_object_or_404(
        User.objects
        .select_related("subscription")
        .annotate(groups_count=Count("event_memberships")),
        id=user_id
    )
    return Response(DashboardUserDetailSerializer(user, context={"request": request}).data)


@swagger_auto_schema(
    method="patch",
    operation_summary="Set user status",
    operation_description="Admin activates or deactivates a user account.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["is_active"],
        properties={
            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="True to activate, False to deactivate"),
        }
    ),
    responses={200: "Status updated", 404: "Not found"},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_user_set_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    is_active = request.data.get("is_active")
    if is_active is None:
        return Response({"detail": "is_active field is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(is_active, bool):
        return Response({"detail": "is_active must be a boolean."}, status=status.HTTP_400_BAD_REQUEST)

    user.is_active = is_active
    user.save()

    return Response({
        "message": f"User {'activated' if user.is_active else 'deactivated'} successfully.",
        "status": "Active" if user.is_active else "Inactive",
    })


@swagger_auto_schema(
    method="delete",
    operation_summary="Delete user",
    operation_description="Admin deletes any user account.",
    responses={200: "Deleted", 404: "Not found"},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return Response({"message": "User deleted successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Send broadcast notification",
    operation_description="Admin sends a notification to all active users.",
    request_body=BroadcastSendSerializer,
    responses={201: "Notification sent", 400: "Validation error"},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_broadcast_send(request):
    serializer = BroadcastSendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    title = serializer.validated_data["title"]
    message = serializer.validated_data["message"]

    users = User.objects.filter(is_active=True).exclude(id=request.user.id)
    Notification.objects.bulk_create([
        Notification(
            recipient=user,
            sender=request.user,
            notification_type="broadcast",
            title=title,
            message=message,
        )
        for user in users
    ])

    return Response({"message": "Broadcast notification sent successfully."}, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method="get",
    operation_summary="List broadcast notifications",
    operation_description="Returns recent broadcast notifications sent by admin with pagination.",
    manual_parameters=[
        openapi.Parameter("page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
    ],
    responses={200: BroadcastNotificationSerializer(many=True)},
    tags=["Dashboard"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@authentication_classes([JWTAuthentication])
def dashboard_broadcast_list(request):
    broadcasts = (
        Notification.objects
        .filter(notification_type="broadcast", sender=request.user)
        .order_by("-created_at")
        .values("title", "message", "created_at")
        .distinct()
    )

    paginator = Paginator(broadcasts, 10)
    page = paginator.get_page(request.query_params.get("page", 1))

    return Response({
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
        "notifications": BroadcastNotificationSerializer(list(page), many=True).data,
    })