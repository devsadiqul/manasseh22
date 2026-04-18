from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification


# Register your models here.
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["email", "name", "phone", "is_email_verified", "is_active", "is_staff", "created_at"]
    list_filter = ["is_active", "is_staff", "is_email_verified", "created_at"]
    search_fields = ["email", "name", "phone"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("name", "phone", "image")}),
        ("Social Auth", {"fields": ("google_id", "apple_id")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified", "groups", "user_permissions")}),
        ("Important Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "phone", "password1", "password2", "is_active", "is_staff"),
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "otp_type", "otp_code", "is_used", "expires_at", "created_at"]
    list_filter = ["otp_type", "is_used", "created_at"]
    search_fields = ["user__email", "otp_code"]
    readonly_fields = ["created_at"]