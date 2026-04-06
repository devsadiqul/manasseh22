from django.contrib import admin
from .models import Subscription, Review


# Register your models here.
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "billing_cycle", "is_active", "is_premium_display", "valid_until", "created_at"]
    list_filter = ["plan", "billing_cycle", "is_active"]
    search_fields = ["user__email"]
    readonly_fields = ["is_premium_display", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("user", "plan", "billing_cycle")}),
        ("Status", {"fields": ("is_active", "valid_until", "is_premium_display")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    @admin.display(boolean=True, description="Is Premium")
    def is_premium_display(self, obj):
        return obj.is_premium


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "rating", "short_review", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["user__email", "review_text"]
    readonly_fields = ["created_at"]

    fieldsets = (
        (None, {"fields": ("user", "rating", "review_text")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="Review")
    def short_review(self, obj):
        if obj.review_text:
            return obj.review_text[:60] + "..." if len(obj.review_text) > 60 else obj.review_text
        return "-"