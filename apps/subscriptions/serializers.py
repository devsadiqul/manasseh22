from rest_framework import serializers
from .models import Subscription, Review


# Create your serializers here.
class SubscriptionSerializer(serializers.ModelSerializer):
    is_premium = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = ["plan", "billing_cycle", "valid_until", "is_active", "is_premium", "created_at", "updated_at"]
        read_only_fields = ["valid_until", "is_active", "created_at", "updated_at"]


class UpgradePlanSerializer(serializers.Serializer):
    billing_cycle = serializers.ChoiceField(choices=["monthly", "yearly"])
    payment_method_token = serializers.CharField(help_text="Payment gateway token")


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "rating", "review_text", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value