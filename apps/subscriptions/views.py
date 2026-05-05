from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from .models import Subscription
from .serializers import SubscriptionSerializer, UpgradePlanSerializer, ReviewSerializer
from .utils import activate_premium_subscription


# Create your views here.
class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get subscription details",
        responses={200: SubscriptionSerializer},
        tags=["Subscription"],
        security=[{"Bearer": []}],
    )
    def get(self, request):
        subscription, _ = Subscription.objects.get_or_create(user=request.user)
        return Response(SubscriptionSerializer(subscription).data)


class UpgradeToPremiumView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Upgrade to premium",
        operation_description="Pass billing_cycle (monthly/yearly) and a payment_method_token.",
        request_body=UpgradePlanSerializer,
        responses={200: SubscriptionSerializer, 400: "Validation error"},
        tags=["Subscription"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = UpgradePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = activate_premium_subscription(request.user, serializer.validated_data["billing_cycle"])
        return Response({
            "detail": "You're now Premium! 🎉",
            "subscription": SubscriptionSerializer(subscription).data,
        })


class ManageSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Cancel subscription",
        operation_description="Downgrades the user back to free plan.",
        responses={200: "Subscription cancelled."},
        tags=["Subscription"],
        security=[{"Bearer": []}],
    )
    def delete(self, request):
        subscription = get_object_or_404(Subscription, user=request.user)
        subscription.plan = "free"
        subscription.billing_cycle = None
        subscription.save()
        return Response({"detail": "Subscription cancelled."}, status=status.HTTP_200_OK)


class ReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Submit app review",
        operation_description="Submit a 1-5 star rating with optional review text.",
        request_body=ReviewSerializer,
        responses={201: ReviewSerializer, 400: "Validation error"},
        tags=["Subscription"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(user=request.user)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)