from rest_framework import serializers
from apps.subscriptions.models import Subscription
from apps.tasks.models import Event
from django.contrib.auth import get_user_model

User = get_user_model()


# Create your serializers here.
class DashboardOverviewSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_groups = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()


class UserGrowthSerializer(serializers.Serializer):
    month = serializers.CharField()
    count = serializers.IntegerField()


class DashboardEventSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="name")
    members = serializers.IntegerField(source="member_count")
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["id", "event_name", "members", "event_date", "created_by"]

    def get_created_by(self, obj):
        return obj.created_by.name


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    is_premium = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = ["plan", "billing_cycle", "valid_until", "is_active", "is_premium"]


class DashboardUserSerializer(serializers.ModelSerializer):
    groups = serializers.IntegerField(source="groups_count")
    subscription = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "image", "groups", "subscription", "status"]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_subscription(self, obj):
        try:
            return obj.subscription.plan if obj.subscription.is_active else "free"
        except Exception:
            return "free"


class DashboardUserDetailSerializer(serializers.ModelSerializer):
    groups = serializers.IntegerField(source="groups_count")
    subscription = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "name", "email", "phone", "image",
            "groups", "subscription", "status",
            "is_email_verified", "created_at",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_subscription(self, obj):
        try:
            return SubscriptionDetailSerializer(obj.subscription).data
        except Exception:
            return {
                "plan": "free",
                "billing_cycle": None,
                "valid_until": None,
                "is_active": True,
                "is_premium": False,
            }
            
            
class BroadcastSendSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    

class BroadcastNotificationSerializer(serializers.Serializer):
    title = serializers.CharField()
    message = serializers.CharField()
    created_at = serializers.DateTimeField()