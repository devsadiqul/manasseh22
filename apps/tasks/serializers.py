from rest_framework import serializers
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from .models import Event, EventMember, Task, TaskComment



# Create your serializers here.
class EventMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = EventMember
        fields = ["id", "user", "role", "joined_at"]


class EventListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    days_left = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Event
        fields = ["id", "name", "cover_image", "event_date", "member_count", "days_left"]

    def get_member_count(self, obj):
        return obj.members.count()

class EventSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    task_count = serializers.IntegerField(read_only=True)
    completed_task_count = serializers.IntegerField(read_only=True)
    days_left = serializers.IntegerField(read_only=True, allow_null=True)
    members_preview = serializers.SerializerMethodField()
    task_progress_percent = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Event
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
                "name": m.user.name,
                "image": m.user.image.url if m.user.image else None,
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


class CreateEventSerializer(serializers.ModelSerializer):
    invite_members = serializers.ListField(
        child=serializers.EmailField(), required=False, write_only=True,
        help_text="List of member emails to invite"
    )

    class Meta:
        model = Event
        fields = ["name", "description", "cover_image", "event_date", "invite_members"]


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ["content"]


class TaskCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ["id", "user", "content", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

 
class MyTaskSerializer(serializers.ModelSerializer):
    event = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "name", "status", "due_date", "event", "assigned_to"]

    def get_event(self, obj):
        return {
            "id": str(obj.event.id),
            "name": obj.event.name,
        }

    def get_assigned_to(self, obj):
        request = self.context.get("request")
        return {
            "id": str(obj.assigned_to.id),
            "name": obj.assigned_to.name,
            "image": request.build_absolute_uri(obj.assigned_to.image.url) if obj.assigned_to.image else None,
        }     


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()
    assigned_to_email = serializers.EmailField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        fields = [
            "id", "event", "name", "description",
            "assigned_to", "assigned_to_email",
            "due_date", "priority", "status", "created_by",
            "comments_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "event", "created_by", "created_at", "updated_at"]

    def get_comments_count(self, obj):
        return obj.comments.count()

    def update(self, instance, validated_data):
        _MISSING = object()
        assigned_email = validated_data.pop("assigned_to_email", _MISSING)

        if assigned_email is not _MISSING:
            if assigned_email:
                instance.assigned_to = User.objects.filter(email=assigned_email).first()
            else:
                instance.assigned_to = None

        return super().update(instance, validated_data)


class TaskDetailSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "name", "description", "due_date",
            "priority", "status", "assigned_to", "activity", "comments"
        ]

    def get_assigned_to(self, obj):
        if not obj.assigned_to:
            return None
        request = self.context.get("request")
        return {
            "id": str(obj.assigned_to.id),
            "name": obj.assigned_to.name,
            "image": request.build_absolute_uri(obj.assigned_to.image.url) if obj.assigned_to.image else None,
        }

    def get_activity(self, obj):
        request = self.context.get("request")
        user_image = request.build_absolute_uri(obj.created_by.image.url) if obj.created_by.image else None
        logs = [
            {
                "user": obj.created_by.name,
                "user_image": user_image,
                "action": "created this task",
                "timestamp": obj.created_at,
            }
        ]
        if obj.updated_at and obj.updated_at != obj.created_at:
            logs.append({
                "user": obj.created_by.name,
                "user_image": user_image,
                "action": "last updated this task",
                "timestamp": obj.updated_at,
            })
        return logs

    def get_comments(self, obj):
        request = self.context.get("request")
        return [
            {
                "id": str(c.id),
                "user": {
                    "id": str(c.user.id),
                    "name": c.user.name,
                    "image": request.build_absolute_uri(c.user.image.url) if c.user.image else None,
                },
                "content": c.content,
                "created_at": c.created_at,
            }
            for c in obj.comments.all()
        ]


class CreateTaskSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.EmailField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        fields = ["name", "description", "assigned_to_email", "due_date", "priority"]