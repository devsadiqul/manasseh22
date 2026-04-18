from django.contrib import admin
from .models import Notification


# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "sender", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["recipient__email", "sender__email", "title", "message"]
    readonly_fields = ["id", "created_at"]

    fieldsets = (
        (None, {"fields": ("id", "notification_type", "title", "message")}),
        ("Users", {"fields": ("recipient", "sender")}),
        ("Related Objects", {"fields": ("related_event", "related_task")}),
        ("Status", {"fields": ("is_read", "created_at")}),
    )

    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("recipient", "sender", "related_event", "related_task")