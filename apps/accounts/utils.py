import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPVerification


def generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


def create_otp(user, otp_type, expiry_minutes=10):
    OTPVerification.objects.filter(user=user, otp_type=otp_type, is_used=False).update(is_used=True)
    otp_code = generate_otp()
    otp = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )
    return otp


def send_otp_email(user, otp_code, otp_type):
    subject_map = {
        "email_verification": "Verify your EventMate email",
        "password_reset": "Reset your EventMate password",
    }
    subject = subject_map.get(otp_type, "Your EventMate OTP")
    message = (
        f"Your OTP code is: {otp_code}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not request this, please ignore this email."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def verify_otp(user, otp_code, otp_type):
    try:
        otp = OTPVerification.objects.filter(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            is_used=False,
        ).latest("created_at")
    except OTPVerification.DoesNotExist:
        return False, "Invalid OTP code."

    if not otp.is_valid():
        return False, "OTP has expired. Please request a new one."

    otp.is_used = True
    otp.save()
    return True, otp


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def get_activity_summary(user):
    from tasks.models import Group, Task
    groups_count = Group.objects.filter(members__user=user).count()
    total_tasks = Task.objects.filter(assigned_to=user).count()
    completed = Task.objects.filter(assigned_to=user, status="completed").count()
    return {"groups": groups_count, "total_tasks": total_tasks, "completed": completed}