from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User
from .serializers import (
    RegisterSerializer, LoginSerializer, OTPVerifySerializer, SendOTPSerializer,
    ResetPasswordSerializer, ChangePasswordSerializer,
    UserSerializer, EditProfileSerializer,
)
from .utils import create_otp, send_otp_email, verify_otp, get_tokens_for_user, get_activity_summary
from apps.subscriptions.utils import create_default_subscription
from apps.subscriptions.serializers import SubscriptionSerializer



# Create your views here.
# ═══════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="Creates a new user account and sends a verification OTP to the email.",
        request_body=RegisterSerializer,
        responses={201: "User registered. OTP sent to email.", 400: "Validation error"},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        create_default_subscription(user)
        otp = create_otp(user, "email_verification")
        send_otp_email(user, otp.otp_code, "email_verification")
        return Response({"detail": "Registration successful. Please verify your email."}, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify email OTP",
        request_body=OTPVerifySerializer,
        responses={200: "Email verified successfully.", 400: "Invalid or expired OTP"},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, email=serializer.validated_data["email"])
        success, result = verify_otp(user, serializer.validated_data["otp_code"], "email_verification")
        if not success:
            return Response({"detail": result}, status=status.HTTP_400_BAD_REQUEST)
        user.is_email_verified = True
        user.save()
        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Login",
        operation_description="Authenticate with email and password. Returns JWT tokens.",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                "Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING),
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                        "user": openapi.Schema(type=openapi.TYPE_OBJECT),
                    },
                ),
            ),
            400: "Invalid credentials",
        },
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)
        return Response({"access": tokens["access"], "refresh": tokens["refresh"], "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Logout",
        operation_description="Blacklists the refresh token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={"refresh": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={205: "Logged out.", 400: "Invalid token."},
        tags=["Auth"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Resend OTP",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "otp_type"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "otp_type": openapi.Schema(type=openapi.TYPE_STRING, enum=["email_verification", "password_reset"]),
            },
        ),
        responses={200: "OTP resent.", 404: "User not found."},
        tags=["Auth"],
    )
    def post(self, request):
        user = get_object_or_404(User, email=request.data.get("email"))
        otp_type = request.data.get("otp_type")
        otp = create_otp(user, otp_type)
        send_otp_email(user, otp.otp_code, otp_type)
        return Response({"detail": "OTP resent."}, status=status.HTTP_200_OK)


class SendPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Send password reset OTP",
        request_body=SendOTPSerializer,
        responses={200: "OTP sent if email is registered."},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
            otp = create_otp(user, "password_reset")
            send_otp_email(user, otp.otp_code, "password_reset")
        except User.DoesNotExist:
            pass
        return Response({"detail": "If this email is registered, an OTP has been sent."}, status=status.HTTP_200_OK)


class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify password reset OTP",
        request_body=OTPVerifySerializer,
        responses={200: "OTP is valid.", 400: "Invalid OTP"},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, email=serializer.validated_data["email"])
        success, result = verify_otp(user, serializer.validated_data["otp_code"], "password_reset")
        if not success:
            return Response({"detail": result}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "OTP verified."}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Reset password",
        request_body=ResetPasswordSerializer,
        responses={200: "Password reset successfully.", 400: "Validation error"},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, email=serializer.validated_data["email"])
        success, result = verify_otp(user, serializer.validated_data["otp_code"], "password_reset")
        if not success:
            return Response({"detail": result}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Password reset successfully."}, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_summary="Get profile",
        operation_description="Returns user profile, subscription info, and activity summary.",
        responses={200: UserSerializer},
        tags=["Profile"],
        security=[{"Bearer": []}],
    )
    def get(self, request):
        subscription = getattr(request.user, "subscription", None)
        activity = get_activity_summary(request.user)
        return Response({
            "user": UserSerializer(request.user).data,
            "subscription": SubscriptionSerializer(subscription).data if subscription else None,
            "activity_summary": activity,
        })

    @swagger_auto_schema(
        operation_summary="Update profile",
        request_body=EditProfileSerializer,
        responses={200: UserSerializer, 400: "Validation error"},
        tags=["Profile"],
        security=[{"Bearer": []}],
    )
    def patch(self, request):
        serializer = EditProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change password",
        request_body=ChangePasswordSerializer,
        responses={200: "Password changed successfully.", 400: "Validation error"},
        tags=["Profile"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["current_password"]):
            return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Delete account",
        operation_description="Permanently deletes the authenticated user's account.",
        responses={204: "Account deleted."},
        tags=["Profile"],
        security=[{"Bearer": []}],
    )
    def delete(self, request):
        request.user.delete()
        return Response({"detail": "Account deleted."}, status=status.HTTP_204_NO_CONTENT)