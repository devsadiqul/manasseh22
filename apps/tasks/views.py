# views.py
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.accounts.models import User
from apps.notifications.utils import send_notification
from .models import Event, EventMember, Task
from .serializers import (
    EventListSerializer, EventSerializer, CreateEventSerializer, EventMemberSerializer, AddMemberSerializer,
    TaskSerializer, TaskDetailSerializer, CreateTaskSerializer, TaskCommentSerializer, CreateCommentSerializer, MyTaskSerializer,
    EventInviteLinkSerializer
)
from django.db.models import Q
from drf_yasg import openapi
from django.utils import timezone



@swagger_auto_schema(
    method="get",
    operation_summary="List events",
    operation_description="Returns events split into owned_events and joined_events. Filter via ?filter=past | upcoming",
    responses={200: EventListSerializer(many=True)},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_list(request):

    filter_type = request.query_params.get("filter", "upcoming")
    now = timezone.now()

    events = Event.objects.filter(
        Q(created_by=request.user) |
        Q(members__user=request.user)
    ).select_related("created_by").prefetch_related("members").distinct()

    if filter_type == "past":
        events = events.filter(event_date__lt=now)
    else:
        events = events.filter(event_date__gte=now)

    events = events.order_by("-event_date")

    owned_events = events.filter(created_by=request.user)
    joined_events = events.exclude(created_by=request.user)

    return Response({
        "filter": filter_type,
        "owned_events": EventListSerializer(
            owned_events, many=True, context={"request": request}
        ).data,
        "joined_events": EventListSerializer(
            joined_events, many=True, context={"request": request}
        ).data,
    })


@swagger_auto_schema(
    method="post",
    operation_summary="Create an event",
    operation_description="Create event (no limit for now).",
    request_body=CreateEventSerializer,
    responses={201: EventSerializer, 400: "Validation error"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def event_create(request):

    invite_members = request.data.getlist("invite_members")

    if len(invite_members) == 1 and "," in invite_members[0]:
        emails = [e.strip() for e in invite_members[0].split(",") if e.strip()]
    else:
        emails = [e.strip() for e in invite_members if e.strip()]


    data = request.data.dict()
    data["invite_members"] = emails

    serializer = CreateEventSerializer(data=data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    invite_emails = serializer.validated_data.pop("invite_members", [])

    event = serializer.save(created_by=request.user)

    EventMember.objects.create(event=event, user=request.user, role="admin")

    for email in invite_emails:
        try:
            member_user = User.objects.get(email=email)
            EventMember.objects.get_or_create(event=event, user=member_user)
        except User.DoesNotExist:
            continue

    return Response(
        {
            "message": "Event created successfully.",
            "event": EventSerializer(event, context={"request": request}).data,
        },
        status=status.HTTP_201_CREATED,
    )


@swagger_auto_schema(
    method="get",
    operation_summary="Get event details",
    operation_description="Returns event info, task list, members, and countdown timer data.",
    responses={200: EventSerializer, 403: "Not a member", 404: "Not found"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_details(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "You are not a member of this event."}, status=status.HTTP_403_FORBIDDEN)

    tasks = event.tasks.select_related("assigned_to")
    members = event.members.select_related("user")

    def format_task(task):
        return {
            "id": str(task.id),
            "name": task.name,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "assigned_to": {
                "id": str(task.assigned_to.id),
                "name": task.assigned_to.name,
                "image": request.build_absolute_uri(task.assigned_to.image.url) if task.assigned_to and task.assigned_to.image else None,
            } if task.assigned_to else None,
        }

    def format_member(m):
        return {
            "id": str(m.user.id),
            "name": m.user.name,
            "image": request.build_absolute_uri(m.user.image.url) if m.user.image else None,
            "role": m.role,
        }

    task_list = list(tasks)

    return Response({
        "id": str(event.id),
        "name": event.name,
        "cover_image": request.build_absolute_uri(event.cover_image.url) if event.cover_image else None,
        "event_date": event.event_date,
        "description": event.description,
        "days_left": event.days_left,
        "is_owner": event.created_by == request.user,
        "task_count": len(task_list),
        "completed_task_count": sum(1 for t in task_list if t.status == "completed"),
        "members": [format_member(m) for m in members],
        "tasks": [format_task(t) for t in task_list],
    })


@swagger_auto_schema(
    method="patch",
    operation_summary="Update event",
    operation_description="Only the event owner can update.",
    request_body=CreateEventSerializer,
    responses={200: EventSerializer, 403: "Not authorized"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def event_update(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "You are not a member of this event."}, status=status.HTTP_403_FORBIDDEN)

    if event.created_by != request.user:
        return Response({"detail": "Only the event owner can update this event."}, status=status.HTTP_403_FORBIDDEN)

    serializer = CreateEventSerializer(event, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.validated_data.pop("invite_members", None)
    serializer.save()
    return Response({
        "message": "Event updated successfully.",
        "event": EventSerializer(event, context={"request": request}).data,
    })


@swagger_auto_schema(
    method="delete",
    operation_summary="Delete event",
    operation_description="Only the event owner can delete.",
    responses={200: "Deleted.", 403: "Not authorized"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def event_delete(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.created_by != request.user:
        return Response({"detail": "Only the event owner can delete this event."}, status=status.HTTP_403_FORBIDDEN)

    event.delete()
    return Response({"message": "Event deleted successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="get",
    operation_summary="List event members",
    manual_parameters=[
        openapi.Parameter("search", openapi.IN_QUERY, description="Search by name, email or phone", type=openapi.TYPE_STRING),
    ],
    responses={200: EventMemberSerializer(many=True)},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_member_list(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    members = event.members.select_related("user").exclude(user=event.created_by)

    search = request.query_params.get("search", "").strip()
    if search:
        members = members.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__phone__icontains=search)
        )

    return Response([
        {
            "id": m.id,
            "name": m.user.name,
            "email": m.user.email,
            "image": request.build_absolute_uri(m.user.image.url) if m.user.image else None,
        }
        for m in members
    ])


@swagger_auto_schema(
    method="post",
    operation_summary="Add member to event",
    operation_description="Add a user by email. Admin only.",
    request_body=AddMemberSerializer,
    responses={201: "Member added", 400: "Already a member", 404: "User not found"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def event_member_add(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.created_by != request.user:
        return Response({"detail": "Only the event owner can add members."}, status=status.HTTP_403_FORBIDDEN)

    serializer = AddMemberSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, email=serializer.validated_data["email"])
    membership, created = EventMember.objects.get_or_create(event=event, user=user)
    if not created:
        return Response({"detail": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)

    send_notification(
        recipient=user,
        sender=request.user,
        notification_type="member_added",
        title="Added to event",
        message=f"{request.user.name} added you to '{event.name}'.",
        related_event=event,
    )

    return Response({
        "message": "Member added successfully.",
        "member": {
            "id": membership.id,
            "name": user.name,
            "email": user.email,
            "image": request.build_absolute_uri(user.image.url) if user.image else None,
        }
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method="delete",
    operation_summary="Remove member from event",
    operation_description="Admin only.",
    responses={200: "Removed.", 403: "Not authorized"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def event_member_remove(request, event_id, member_id):
    event = get_object_or_404(Event, id=event_id, created_by=request.user)
    membership = get_object_or_404(EventMember, event=event, id=member_id)
    membership.delete()
    return Response({"message": "Member removed successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="get",
    operation_summary="Get event invite link",
    operation_description="Returns a shareable invite link for the event. Admin/owner only.",
    responses={200: EventInviteLinkSerializer, 403: "Forbidden"},
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_invite_link(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    is_admin_member = EventMember.objects.filter(
        event=event, user=request.user, role="admin"
    ).exists()

    if event.created_by != request.user and not is_admin_member:
        return Response(
            {"detail": "Only the event owner or admins can access the invite link."},
            status=status.HTTP_403_FORBIDDEN,
        )

    invite_link = request.build_absolute_uri(
        f"/api/events/join/{event.invite_token}/"
    )

    return Response({"invite_link": invite_link}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="get",
    operation_summary="Join event via invite link",
    operation_description="Authenticated user joins the event using the invite token from the link.",
    responses={
        200: "Already a member",
        201: "Joined successfully",
        404: "Invalid or expired invite token",
    },
    tags=["Events"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_join_by_invite(request, token):
    event = get_object_or_404(Event, invite_token=token)

    membership, created = EventMember.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={"role": "member"},
    )

    if not created:
        return Response(
            {"detail": "You are already a member of this event."},
            status=status.HTTP_200_OK,
        )

    send_notification(
        recipient=event.created_by,
        sender=request.user,
        notification_type="member_joined",
        title="New member joined",
        message=f"{request.user.name} joined '{event.name}' via invite link.",
        related_event=event,
    )

    return Response(
        {
            "message": "Successfully joined the event.",
            "event": {
                "id": event.id,
                "name": event.name,
                "event_date": event.event_date,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@swagger_auto_schema(
    method="get",
    operation_summary="List tasks in an event",
    responses={200: TaskSerializer(many=True)},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_list(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    tasks = event.tasks.select_related("assigned_to", "created_by").prefetch_related("comments")
    return Response(TaskSerializer(tasks, many=True).data)


@swagger_auto_schema(
    method="get",
    operation_summary="Get my assigned tasks",
    operation_description="Returns all pending tasks assigned to the logged in user.",
    responses={200: MyTaskSerializer(many=True)},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_task_list(request):
    tasks = list(
        Task.objects
        .filter(assigned_to=request.user, status="pending")
        .select_related("event", "assigned_to")
        .order_by("due_date")
    )

    return Response({
        "pending_count": len(tasks),
        "tasks": MyTaskSerializer(tasks, many=True, context={"request": request}).data,
    })


@swagger_auto_schema(
    method="post",
    operation_summary="Create a task",
    operation_description="Assign by email. Assignee gets a notification.",
    request_body=CreateTaskSerializer,
    responses={201: "Task created", 400: "Validation error", 403: "Not a member"},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def task_create(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    serializer = CreateTaskSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assigned_email = serializer.validated_data.pop("assigned_to_email", None)
    assigned_user = User.objects.filter(email=assigned_email).first() if assigned_email else None

    task = Task.objects.create(
        event=event,
        created_by=request.user,
        assigned_to=assigned_user,
        **serializer.validated_data,
    )

    if assigned_user and assigned_user != request.user:
        send_notification(
            recipient=assigned_user,
            sender=request.user,
            notification_type="task_assigned",
            title="Task assigned to you",
            message=f"You've been assigned '{task.name}' in '{event.name}'.",
            related_event=event,
            related_task=task,
        )

    return Response({
        "message": "Task created successfully.",
        "task": {
            "id": str(task.id),
            "name": task.name,
            "priority": task.priority,
            "due_date": task.due_date,
            "status": task.status,
            "assigned_to": {
                "id": str(assigned_user.id),
                "name": assigned_user.name,
                "image": request.build_absolute_uri(assigned_user.image.url) if assigned_user.image else None,
            } if assigned_user else None,
        }
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method="get",
    operation_summary="Get task details",
    operation_description="Includes comments and activity log.",
    responses={200: TaskDetailSerializer},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_details(request, event_id, task_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    task = get_object_or_404(
        Task.objects.select_related("assigned_to", "created_by").prefetch_related("comments__user"),
        id=task_id, event=event
    )
    return Response(TaskDetailSerializer(task, context={"request": request}).data)


@swagger_auto_schema(
    method="patch",
    operation_summary="Update task",
    operation_description="Pass assigned_to_email to change assignee. Pass null to unassign.",
    request_body=TaskSerializer,
    responses={200: "Task updated"},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def task_update(request, event_id, task_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    task = get_object_or_404(Task, id=task_id, event=event)
    old_assignee = task.assigned_to

    serializer = TaskSerializer(task, data=request.data, partial=True, context={"request": request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    updated_task = serializer.save()
    new_assignee = updated_task.assigned_to

    if new_assignee and new_assignee != old_assignee and new_assignee != request.user:
        send_notification(
            recipient=new_assignee,
            sender=request.user,
            notification_type="task_assigned",
            title="Task assigned to you",
            message=f"You've been assigned '{updated_task.name}' in '{event.name}'.",
            related_event=event,
            related_task=updated_task,
        )

    return Response({
        "message": "Task updated successfully.",
        "task": {
            "id": str(updated_task.id),
            "name": updated_task.name,
            "description": updated_task.description,
            "due_date": updated_task.due_date,
            "priority": updated_task.priority,
            "status": updated_task.status,
            "assigned_to": {
                "id": str(new_assignee.id),
                "name": new_assignee.name,
                "image": request.build_absolute_uri(new_assignee.image.url) if new_assignee.image else None,
            } if new_assignee else None,
        }
    })


@swagger_auto_schema(
    method="delete",
    operation_summary="Delete task",
    responses={200: "Deleted."},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def task_delete(request, event_id, task_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    task = get_object_or_404(Task, id=task_id, event=event)
    task.delete()
    return Response({"message": "Task deleted successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Toggle task complete / incomplete",
    operation_description="Notifies all event members when toggled.",
    responses={200: TaskSerializer},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def task_mark_complete(request, event_id, task_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    task = get_object_or_404(Task, id=task_id, event=event)
    task.status = "completed" if task.status == "pending" else "pending"
    task.save()

    for membership in event.members.exclude(user=request.user).select_related("user"):
        send_notification(
            recipient=membership.user,
            sender=request.user,
            notification_type="task_completed",
            title="Task completed",
            message=f"{request.user.name} completed task '{task.name}'.",
            related_event=event,
            related_task=task,
        )
    return Response({
        "message": "Task marked as completed." if task.status == "completed" else "Task marked as pending.",
        "task": TaskSerializer(task).data,
    })


@swagger_auto_schema(
    method="get",
    operation_summary="List comments on a task",
    responses={200: TaskCommentSerializer(many=True)},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_comment_list(request, event_id, task_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    task = get_object_or_404(Task, id=task_id, event=event)
    comments = task.comments.select_related("user").order_by("created_at")
    return Response(TaskCommentSerializer(comments, many=True).data)


@swagger_auto_schema(
    method="post",
    operation_summary="Add comment to a task",
    request_body=CreateCommentSerializer,
    responses={201: "Comment added"},
    tags=["Tasks"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def task_comment_create(request, event_id, task_id):
    event = get_object_or_404(Event, id=event_id)

    if not event.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)

    task = get_object_or_404(Task, id=task_id, event=event)

    serializer = CreateCommentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    comment = serializer.save(task=task, user=request.user)

    if task.assigned_to and task.assigned_to != request.user:
        send_notification(
            recipient=task.assigned_to,
            sender=request.user,
            notification_type="task_comment",
            title="New comment on your task",
            message=f"{request.user.name} commented on '{task.name}'.",
            related_task=task,
        )

    return Response({
        "message": "Comment added successfully.",
        "comment": {
            "id": str(comment.id),
            "user": {
                "id": str(request.user.id),
                "name": request.user.name,
                "image": request.build_absolute_uri(request.user.image.url) if request.user.image else None,
            },
            "content": comment.content,
            "created_at": comment.created_at,
        }
    }, status=status.HTTP_201_CREATED)