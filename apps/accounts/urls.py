from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views


# Create your urls here.
urlpatterns = [
    # Auth
    path("auth/register/", views.register, name="auth-register"),
    path("auth/verify-email/", views.verify_email, name="auth-verify-email"),
    path("auth/login/", views.login, name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/resend-otp/", views.resend_otp, name="auth-resend-otp"),
    path("auth/forgot-password/send-otp/", views.send_password_reset_otp, name="auth-forgot-send-otp"),
    path("auth/forgot-password/verify-otp/", views.verify_password_reset_otp, name="auth-forgot-verify-otp"),
    path("auth/forgot-password/reset/", views.reset_password, name="auth-reset-password"),

    # Profile
    path("profile/", views.get_profile, name="profile-get"),
    path("profile/update/", views.update_profile, name="profile-update"),
    path("profile/change-password/", views.change_password, name="profile-change-password"),
    path("profile/delete-account/", views.delete_account, name="profile-delete-account"),
]