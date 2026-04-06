from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from apps.accounts.models import User
from apps.notifications.utils import send_notification
from .models import Group, GroupMember, Task
from .serializers import (
    GroupSerializer, CreateGroupSerializer, GroupMemberSerializer, AddMemberSerializer,
    TaskSerializer, TaskDetailSerializer, CreateTaskSerializer, TaskCommentSerializer,
)


# Create your views here.
# ═══════════════════════════════════════════════════════
# GROUP VIEWS
# ═══════════════════════════════════════════════════════

class GroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_summary="List groups",
        operation_description="Returns groups split into 'your_groups' (owned) and 'group_joined' (member).",
        responses={200: GroupSerializer(many=True)},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def get(self, request):
        member_group_ids = GroupMember.objects.filter(user=request.user).values_list("group_id", flat=True)
        groups = Group.objects.filter(id__in=member_group_ids).prefetch_related("members", "tasks")
        serializer = GroupSerializer(groups, many=True, context={"request": request})
        owned = [g for g in serializer.data if g["is_owner"]]
        joined = [g for g in serializer.data if not g["is_owner"]]
        return Response({"your_groups": owned, "group_joined": joined})

    @swagger_auto_schema(
        operation_summary="Create a group",
        operation_description="Free plan: max 3 groups. Premium: unlimited.",
        request_body=CreateGroupSerializer,
        responses={201: GroupSerializer, 400: "Validation error", 403: "Group limit reached"},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        subscription = getattr(request.user, "subscription", None)
        if not (subscription and subscription.is_premium):
            owned_count = Group.objects.filter(created_by=request.user).count()
            if owned_count >= 3:
                return Response(
                    {"detail": "Free plan allows a maximum of 3 groups. Upgrade to Premium for unlimited groups."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite_emails = serializer.validated_data.pop("invite_members", [])
        group = serializer.save(created_by=request.user)
        GroupMember.objects.create(group=group, user=request.user, role="admin")
        for email in invite_emails:
            try:
                member_user = User.objects.get(email=email)
                GroupMember.objects.get_or_create(group=group, user=member_user)
                send_notification(
                    recipient=member_user,
                    sender=request.user,
                    notification_type="member_added",
                    title="You were added to a group",
                    message=f"{request.user.full_name} added you to '{group.name}'.",
                    related_group=group,
                )
            except User.DoesNotExist:
                pass
        return Response(GroupSerializer(group, context={"request": request}).data, status=status.HTTP_201_CREATED)


class GroupDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_group(self, group_id, user, require_owner=False):
        group = get_object_or_404(Group, id=group_id)
        if require_owner and group.created_by != user:
            return None, Response({"detail": "Only the group owner can perform this action."}, status=status.HTTP_403_FORBIDDEN)
        if not group.members.filter(user=user).exists():
            return None, Response({"detail": "You are not a member of this group."}, status=status.HTTP_403_FORBIDDEN)
        return group, None

    @swagger_auto_schema(
        operation_summary="Get group details",
        operation_description="Returns group info, task list, members, and countdown timer data.",
        responses={200: GroupSerializer, 403: "Not a member", 404: "Not found"},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def get(self, request, group_id):
        group, err = self._get_group(group_id, request.user)
        if err:
            return err
        tasks = group.tasks.select_related("assigned_to", "created_by").prefetch_related("comments")
        members = group.members.select_related("user")
        return Response({
            "group": GroupSerializer(group, context={"request": request}).data,
            "tasks": TaskSerializer(tasks, many=True).data,
            "members": GroupMemberSerializer(members, many=True).data,
        })

    @swagger_auto_schema(
        operation_summary="Update group",
        operation_description="Only the group owner/admin can update.",
        request_body=CreateGroupSerializer,
        responses={200: GroupSerializer, 403: "Not authorized"},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def patch(self, request, group_id):
        group, err = self._get_group(group_id, request.user, require_owner=True)
        if err:
            return err
        serializer = CreateGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("invite_members", None)
        serializer.save()
        return Response(GroupSerializer(group, context={"request": request}).data)

    @swagger_auto_schema(
        operation_summary="Delete group",
        operation_description="Only the group owner can delete.",
        responses={204: "Deleted.", 403: "Not authorized"},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def delete(self, request, group_id):
        group, err = self._get_group(group_id, request.user, require_owner=True)
        if err:
            return err
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List group members",
        responses={200: GroupMemberSerializer(many=True)},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        members = group.members.select_related("user")
        return Response(GroupMemberSerializer(members, many=True).data)

    @swagger_auto_schema(
        operation_summary="Add member to group",
        operation_description="Add a user by email. Admin only.",
        request_body=AddMemberSerializer,
        responses={201: GroupMemberSerializer, 400: "Already a member", 404: "User not found"},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id, created_by=request.user)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, email=serializer.validated_data["email"])
        membership, created = GroupMember.objects.get_or_create(group=group, user=user)
        if not created:
            return Response({"detail": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)
        send_notification(
            recipient=user,
            sender=request.user,
            notification_type="member_added",
            title="Added to group",
            message=f"{request.user.full_name} added you to '{group.name}'.",
            related_group=group,
        )
        return Response(GroupMemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class RemoveMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Remove member from group",
        operation_description="Admin only.",
        responses={204: "Removed.", 403: "Not authorized"},
        tags=["Groups"],
        security=[{"Bearer": []}],
    )
    def delete(self, request, group_id, user_id):
        group = get_object_or_404(Group, id=group_id, created_by=request.user)
        membership = get_object_or_404(GroupMember, group=group, user__id=user_id)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════
# TASK VIEWS
# ═══════════════════════════════════════════════════════

class TaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List tasks in a group",
        responses={200: TaskSerializer(many=True)},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if not group.members.filter(user=request.user).exists():
            return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)
        tasks = group.tasks.select_related("assigned_to", "created_by").prefetch_related("comments")
        return Response(TaskSerializer(tasks, many=True).data)

    @swagger_auto_schema(
        operation_summary="Create a task",
        operation_description="Assign by email. Assignee gets a notification.",
        request_body=CreateTaskSerializer,
        responses={201: TaskSerializer, 400: "Validation error", 403: "Not a member"},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if not group.members.filter(user=request.user).exists():
            return Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CreateTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned_email = serializer.validated_data.pop("assigned_to_email", None)
        assigned_user = User.objects.filter(email=assigned_email).first() if assigned_email else None
        task = Task.objects.create(
            group=group,
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
                message=f"You've been assigned '{task.name}' in '{group.name}'.",
                related_group=group,
                related_task=task,
            )
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_task(self, group_id, task_id, user):
        group = get_object_or_404(Group, id=group_id)
        if not group.members.filter(user=user).exists():
            return None, None, Response({"detail": "Not a member."}, status=status.HTTP_403_FORBIDDEN)
        task = get_object_or_404(Task, id=task_id, group=group)
        return group, task, None

    @swagger_auto_schema(
        operation_summary="Get task details",
        operation_description="Includes comments and activity log.",
        responses={200: TaskDetailSerializer},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def get(self, request, group_id, task_id):
        _, task, err = self._get_task(group_id, task_id, request.user)
        if err:
            return err
        return Response(TaskDetailSerializer(task).data)

    @swagger_auto_schema(
        operation_summary="Update task",
        request_body=TaskSerializer,
        responses={200: TaskSerializer},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def patch(self, request, group_id, task_id):
        _, task, err = self._get_task(group_id, task_id, request.user)
        if err:
            return err
        serializer = TaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Delete task",
        responses={204: "Deleted."},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def delete(self, request, group_id, task_id):
        _, task, err = self._get_task(group_id, task_id, request.user)
        if err:
            return err
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Toggle task complete / incomplete",
        operation_description="Notifies all group members when toggled.",
        responses={200: TaskSerializer},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def post(self, request, group_id, task_id):
        group = get_object_or_404(Group, id=group_id)
        task = get_object_or_404(Task, id=task_id, group=group)
        task.status = "completed" if task.status == "pending" else "pending"
        task.save()
        for membership in group.members.exclude(user=request.user).select_related("user"):
            send_notification(
                recipient=membership.user,
                sender=request.user,
                notification_type="task_completed",
                title="Task completed",
                message=f"{request.user.full_name} completed task '{task.name}'.",
                related_group=group,
                related_task=task,
            )
        return Response(TaskSerializer(task).data)


class TaskCommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List comments on a task",
        responses={200: TaskCommentSerializer(many=True)},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def get(self, request, group_id, task_id):
        task = get_object_or_404(Task, id=task_id, group__id=group_id)
        comments = task.comments.select_related("user").order_by("created_at")
        return Response(TaskCommentSerializer(comments, many=True).data)

    @swagger_auto_schema(
        operation_summary="Add comment to a task",
        request_body=TaskCommentSerializer,
        responses={201: TaskCommentSerializer},
        tags=["Tasks"],
        security=[{"Bearer": []}],
    )
    def post(self, request, group_id, task_id):
        task = get_object_or_404(Task, id=task_id, group__id=group_id)
        serializer = TaskCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task, user=request.user)
        if task.assigned_to and task.assigned_to != request.user:
            send_notification(
                recipient=task.assigned_to,
                sender=request.user,
                notification_type="task_comment",
                title="New comment on your task",
                message=f"{request.user.full_name} commented on '{task.name}'.",
                related_task=task,
            )
        return Response(TaskCommentSerializer(comment).data, status=status.HTTP_201_CREATED)