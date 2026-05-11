from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.response import Response
from django.contrib.auth import authenticate
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
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


# ═══════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════

@swagger_auto_schema(
    method="post",
    operation_summary="Register a new user",
    operation_description="Creates a new user account and sends a verification OTP to the email.",
    request_body=RegisterSerializer,
    responses={201: "User registered. OTP sent to email.", 400: "Validation error"},
    tags=["auth"],
)
@api_view(["POST"])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data.get("email")
    if User.objects.filter(email=email).exists():
        return Response({"detail": "This email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

    if not serializer.validated_data.get("agreed_to_terms"):
        return Response({"detail": "You must agree to the Terms of Use & Privacy Policy."}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    create_default_subscription(user)
    otp = create_otp(user, "email_verification")
    send_otp_email(user, otp.otp_code, "email_verification")
    return Response({"message": "Registration successful. Please verify your email."}, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method="post",
    operation_summary="Verify email OTP",
    request_body=OTPVerifySerializer,
    responses={200: "Email verified successfully.", 400: "Invalid or expired OTP"},
    tags=["auth"],
)
@api_view(["POST"])
def verify_email(request):
    serializer = OTPVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = get_object_or_404(User, email=serializer.validated_data["email"])

    if user.is_email_verified:
        return Response({"detail": "Email already verified."}, status=status.HTTP_400_BAD_REQUEST)

    success, message = verify_otp(
        user,
        serializer.validated_data["otp_code"],
        "email_verification"
    )

    if not success:
        return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    tokens = get_tokens_for_user(user)
    user_data = UserSerializer(user, context={"request": request}).data

    return Response({
        "message": message,
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": user_data
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Login",
    operation_description="Authenticate with email and password. Returns JWT tokens.",
    request_body=LoginSerializer,
    responses={200: "Login successful", 400: "Invalid credentials"},
    tags=["auth"],
)
@api_view(["POST"])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(email=serializer.validated_data["email"], password=serializer.validated_data["password"])
    if not user:
        return Response({"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

    if not user.is_email_verified:
        return Response({"detail": "Email is not verified."}, status=status.HTTP_400_BAD_REQUEST)

    tokens = get_tokens_for_user(user)
    return Response({
        "message": "Login successful.",
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": UserSerializer(user).data,
    })


@swagger_auto_schema(
    method="post",
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
    tags=["auth"],
)
@api_view(["POST"])
def resend_otp(request):
    email = request.data.get("email")
    otp_type = request.data.get("otp_type")

    if not email or not otp_type:
        return Response({"detail": "email and otp_type are required."}, status=status.HTTP_400_BAD_REQUEST)

    if otp_type not in ["email_verification", "password_reset"]:
        return Response({"detail": "Invalid otp_type."}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, email=email)
    otp = create_otp(user, otp_type)
    send_otp_email(user, otp.otp_code, otp_type)
    return Response({"message": "OTP resent successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Send password reset OTP",
    request_body=SendOTPSerializer,
    responses={200: "OTP sent if email is registered."},
    tags=["auth"],
)
@api_view(["POST"])
def send_password_reset_otp(request):
    serializer = SendOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=serializer.validated_data["email"])
        otp = create_otp(user, "password_reset")
        send_otp_email(user, otp.otp_code, "password_reset")
    except User.DoesNotExist:
        pass

    return Response({"message": "If this email is registered, an OTP has been sent."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Verify password reset OTP",
    request_body=OTPVerifySerializer,
    responses={200: "OTP is valid.", 400: "Invalid OTP"},
    tags=["auth"],
)
@api_view(["POST"])
def verify_password_reset_otp(request):
    serializer = OTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, email=serializer.validated_data["email"])
    success, result = verify_otp(user, serializer.validated_data["otp_code"], "password_reset")
    if not success:
        return Response({"detail": result}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Reset password",
    request_body=ResetPasswordSerializer,
    responses={200: "Password reset successfully.", 400: "Validation error"},
    tags=["auth"],
)
@api_view(["POST"])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, email=serializer.validated_data["email"])
    user.set_password(serializer.validated_data["new_password"])
    user.save()
    return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="get",
    operation_summary="Get profile",
    operation_description="Returns user profile, subscription info, and activity summary.",
    responses={200: UserSerializer},
    tags=["Profile"],
    security=[{"Bearer": []}],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    subscription = getattr(request.user, "subscription", None)
    activity = get_activity_summary(request.user)
    return Response({
        "user": UserSerializer(request.user, context={'request': request}).data,
        "subscription": SubscriptionSerializer(subscription).data if subscription else None,
        "activity_summary": activity,
    })


@swagger_auto_schema(
    method="patch",
    operation_summary="Update profile",
    request_body=EditProfileSerializer,
    responses={200: UserSerializer, 400: "Validation error"},
    tags=["Profile"],
    security=[{"Bearer": []}],
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    serializer = EditProfileSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response({
        "message": "Profile updated successfully.",
        "user": UserSerializer(request.user, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Change password",
    request_body=ChangePasswordSerializer,
    responses={200: "Password changed successfully.", 400: "Validation error"},
    tags=["Profile"],
    security=[{"Bearer": []}],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if not request.user.check_password(serializer.validated_data["current_password"]):
        return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(serializer.validated_data["new_password"])
    request.user.save()
    return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="delete",
    operation_summary="Delete account",
    operation_description="Permanently deletes the authenticated user's account.",
    responses={200: "Account deleted."},
    tags=["Profile"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    request.user.delete()
    return Response({"message": "Account deleted successfully."}, status=status.HTTP_200_OK)



@swagger_auto_schema(
    method="post",
    operation_summary="Google Login",
    operation_description="Send id_token from Google Sign-In SDK. Returns JWT tokens.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["id_token"],
        properties={
            "id_token": openapi.Schema(type=openapi.TYPE_STRING, description="ID token from Google SDK"),
        }
    ),
    responses={200: "Login successful", 400: "Invalid token"},
    tags=["auth"],
)
@api_view(["POST"])
def google_login(request):
    token = request.data.get("id_token")
    if not token:
        return Response({"detail": "id_token required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

    email = idinfo.get("email")
    name = idinfo.get("name", "")
    picture = idinfo.get("picture", None)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"name": name, "is_email_verified": True}
    )

    tokens = get_tokens_for_user(user)
    return Response({
        "message": "Login successful.",
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": UserSerializer(user).data,
    })


@swagger_auto_schema(
    method="post",
    operation_summary="Apple Login",
    operation_description="Send id_token from Apple Sign-In SDK. Returns JWT tokens.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["id_token"],
        properties={
            "id_token": openapi.Schema(type=openapi.TYPE_STRING, description="ID token from Apple SDK"),
            "name": openapi.Schema(type=openapi.TYPE_STRING, description="User name (only on first login)"),
        }
    ),
    responses={200: "Login successful", 400: "Invalid token"},
    tags=["auth"],
)
@api_view(["POST"])
def apple_login(request):
    from jwt import PyJWKClient
    from jwt import decode as jwt_decode

    id_token_str = request.data.get("id_token")
    if not id_token_str:
        return Response({"detail": "id_token required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        jwks_client = PyJWKClient("https://appleid.apple.com/auth/keys")
        signing_key = jwks_client.get_signing_key_from_jwt(id_token_str)
        payload = jwt_decode(
            id_token_str,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID,
        )
    except Exception:
        return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

    email = payload.get("email")
    if not email:
        return Response({"detail": "Email not found in token."}, status=status.HTTP_400_BAD_REQUEST)

    name = request.data.get("name", email.split("@")[0])

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"name": name, "is_email_verified": True}
    )

    tokens = get_tokens_for_user(user)
    return Response({
        "message": "Login successful.",
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": UserSerializer(user).data,
    })
    
    
@swagger_auto_schema(
    method="delete",
    operation_summary="Delete account",
    operation_description="Permanently deletes the authenticated user's account.",
    responses={200: "Account deleted", 401: "Unauthorized"},
    tags=["auth"],
    security=[{"Bearer": []}],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    user = request.user
    user.delete()
    return Response({"message": "Account deleted successfully."}, status=status.HTTP_200_OK)