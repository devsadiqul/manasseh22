from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Group, GroupMember, Task, TaskComment


# Create your serializers here.
class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMember
        fields = ["id", "user", "role", "joined_at"]


class GroupSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    task_count = serializers.IntegerField(read_only=True)
    completed_task_count = serializers.IntegerField(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    members_preview = serializers.SerializerMethodField()
    task_progress_percent = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            "id", "name", "description", "cover_image", "event_date",
            "created_by", "member_count", "task_count", "completed_task_count",
            "task_progress_percent", "days_left", "members_preview",
            "is_owner", "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_members_preview(self, obj):
        members = obj.members.select_related("user")[:3]
        return [
            {
                "id": str(m.user.id),
                "full_name": m.user.full_name,
                "profile_picture": m.user.profile_picture.url if m.user.profile_picture else None,
            }
            for m in members
        ]

    def get_task_progress_percent(self, obj):
        total = obj.task_count
        if total == 0:
            return 0
        return round((obj.completed_task_count / total) * 100)

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user:
            return obj.created_by == request.user
        return False


class CreateGroupSerializer(serializers.ModelSerializer):
    invite_members = serializers.ListField(
        child=serializers.EmailField(), required=False, write_only=True,
        help_text="List of member emails to invite"
    )

    class Meta:
        model = Group
        fields = ["name", "description", "cover_image", "event_date", "invite_members"]


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()


class TaskCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ["id", "user", "content", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "group", "name", "description", "assigned_to",
            "due_date", "priority", "status", "created_by",
            "comments_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "group", "created_by", "created_at", "updated_at"]

    def get_comments_count(self, obj):
        return obj.comments.count()


class TaskDetailSerializer(TaskSerializer):
    comments = TaskCommentSerializer(many=True, read_only=True)
    activity = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ["comments", "activity"]

    def get_activity(self, obj):
        return [
            {
                "user": obj.created_by.full_name,
                "action": "created this task",
                "timestamp": obj.created_at,
            }
        ]


class CreateTaskSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.EmailField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        fields = ["name", "description", "assigned_to_email", "due_date", "priority"]