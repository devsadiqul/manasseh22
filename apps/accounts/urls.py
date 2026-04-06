from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views


# Create your urls here.
urlpatterns = [
    # Auth
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/verify-email/", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/resend-otp/", views.ResendOTPView.as_view(), name="auth-resend-otp"),
    path("auth/forgot-password/send-otp/", views.SendPasswordResetOTPView.as_view(), name="auth-forgot-send-otp"),
    path("auth/forgot-password/verify-otp/", views.VerifyPasswordResetOTPView.as_view(), name="auth-forgot-verify-otp"),
    path("auth/forgot-password/reset/", views.ResetPasswordView.as_view(), name="auth-reset-password"),

    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/change-password/", views.ChangePasswordView.as_view(), name="profile-change-password"),
    path("profile/delete-account/", views.DeleteAccountView.as_view(), name="profile-delete-account"),
]