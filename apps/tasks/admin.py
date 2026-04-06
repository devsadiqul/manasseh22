from django.contrib import admin
from .models import Group, GroupMember, Task, TaskComment


# Register your models here.
class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0
    readonly_fields = ["joined_at"]
    fields = ["user", "role", "joined_at"]


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    readonly_fields = ["id", "created_at"]
    fields = ["name", "assigned_to", "priority", "status", "due_date"]
    show_change_link = True


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "event_date", "days_left_display", "task_count_display", "completed_task_count_display", "created_at"]
    list_filter = ["event_date", "created_at"]
    search_fields = ["name", "description", "created_by__email"]
    readonly_fields = ["id", "days_left_display", "task_count_display", "completed_task_count_display", "created_at", "updated_at"]
    inlines = [GroupMemberInline, TaskInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "description", "cover_image")}),
        ("Event", {"fields": ("event_date", "days_left_display")}),
        ("Stats", {"fields": ("task_count_display", "completed_task_count_display")}),
        ("Meta", {"fields": ("created_by", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by")

    @admin.display(description="Days Left")
    def days_left_display(self, obj):
        return obj.days_left if obj.days_left is not None else "-"

    @admin.display(description="Total Tasks")
    def task_count_display(self, obj):
        return obj.task_count

    @admin.display(description="Completed Tasks")
    def completed_task_count_display(self, obj):
        return obj.completed_task_count


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "group", "role", "joined_at"]
    list_filter = ["role", "joined_at"]
    search_fields = ["user__email", "group__name"]
    readonly_fields = ["joined_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "group")


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ["id", "created_at"]
    fields = ["user", "content", "created_at"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "assigned_to", "priority", "status", "due_date", "created_at"]
    list_filter = ["priority", "status", "due_date", "created_at"]
    search_fields = ["name", "description", "assigned_to__email", "group__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [TaskCommentInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "description")}),
        ("Assignment", {"fields": ("group", "assigned_to", "created_by")}),
        ("Details", {"fields": ("priority", "status", "due_date")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("group", "assigned_to", "created_by")


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ["user", "task", "short_content", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "task__name", "content"]
    readonly_fields = ["id", "created_at"]

    fieldsets = (
        (None, {"fields": ("id", "task", "user", "content")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "task")

    @admin.display(description="Comment")
    def short_content(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content