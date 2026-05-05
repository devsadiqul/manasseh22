from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from .serializers import ContactSerializer, FAQSerializer, FAQCategorySerializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from django.core.mail import EmailMessage
from rest_framework import status
from django.conf import settings
from .models import FAQ, FAQCategory
from django.db.models import Q
from drf_yasg import openapi


# Create your views here.
@swagger_auto_schema(
    method='post',
    request_body=ContactSerializer,
    responses={201: ContactSerializer, 400: 'Bad Request'},
    operation_summary="Send a contact message",
    tags=['Contact']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def send_message(request):
    serializer = ContactSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data

        email_body = (
            f"Hello Admin,\n\n"
            f"{data['message']}\n\n"
            f"Best regards,\n"
            f"{data['name']}"
        )

        email = EmailMessage(
            subject=f"[Contact] {data['subject']}",
            body=email_body,
            from_email=settings.EMAIL_HOST_USER,
            to=[settings.ADMIN_EMAIL],
            reply_to=[f"{data['name']} <{data['email']}>"],
        )
        email.send(fail_silently=False)

        return Response({'message': 'Your message has been sent successfully.'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── FAQ Category Views ───────────────────────────────────────────────────────

@swagger_auto_schema(
    method='get',
    responses={200: FAQCategorySerializer(many=True)},
    operation_summary="List all active FAQ categories",
    tags=['FAQ']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def faq_category_list(request):
    categories = FAQCategory.objects.filter(is_active=True)
    serializer = FAQCategorySerializer(categories, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    request_body=FAQCategorySerializer,
    responses={201: FAQCategorySerializer, 400: 'Bad Request'},
    operation_summary="Create a new FAQ category (Admin only)",
    tags=['FAQ']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def faq_category_create(request):
    serializer = FAQCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='patch',
    request_body=FAQCategorySerializer,
    responses={200: FAQCategorySerializer, 400: 'Bad Request', 404: 'Not Found'},
    operation_summary="Update a FAQ category (Admin only)",
    tags=['FAQ']
)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def faq_category_update(request, pk):
    try:
        category = FAQCategory.objects.get(pk=pk)
    except FAQCategory.DoesNotExist:
        return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = FAQCategorySerializer(category, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    responses={204: 'No Content', 404: 'Not Found'},
    operation_summary="Delete a FAQ category (Admin only)",
    tags=['FAQ']
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def faq_category_delete(request, pk):
    try:
        category = FAQCategory.objects.get(pk=pk)
    except FAQCategory.DoesNotExist:
        return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)
    category.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── FAQ Views ────────────────────────────────────────────────────────────────

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('category', openapi.IN_QUERY, description="Filter by category ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by question or answer", type=openapi.TYPE_STRING),
    ],
    responses={200: FAQSerializer(many=True)},
    operation_summary="List all active FAQs",
    tags=['FAQ']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def faq_list(request):
    faqs = FAQ.objects.select_related('category').filter(
        is_active=True,
        category__is_active=True
    ).order_by('order')

    category_id = request.query_params.get('category')
    if category_id:
        faqs = faqs.filter(category__id=category_id)

    search = request.query_params.get('search')
    if search:
        faqs = faqs.filter(
            Q(question__icontains=search) |
            Q(answer__icontains=search)
        )

    serializer = FAQSerializer(faqs, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    request_body=FAQSerializer,
    responses={201: FAQSerializer, 400: 'Bad Request'},
    operation_summary="Create a new FAQ (Admin only)",
    tags=['FAQ']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def faq_create(request):
    serializer = FAQSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    responses={200: FAQSerializer, 404: 'Not Found'},
    operation_summary="Retrieve a single FAQ",
    tags=['FAQ']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def faq_detail(request, pk):
    try:
        faq = FAQ.objects.select_related('category').get(pk=pk, is_active=True)
    except FAQ.DoesNotExist:
        return Response({'error': 'FAQ not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = FAQSerializer(faq)
    return Response(serializer.data)


@swagger_auto_schema(
    method='patch',
    request_body=FAQSerializer,
    responses={200: FAQSerializer, 400: 'Bad Request', 404: 'Not Found'},
    operation_summary="Update a FAQ (Admin only)",
    tags=['FAQ']
)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def faq_update(request, pk):
    try:
        faq = FAQ.objects.get(pk=pk, is_active=True)
    except FAQ.DoesNotExist:
        return Response({'error': 'FAQ not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = FAQSerializer(faq, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    responses={204: 'No Content', 404: 'Not Found'},
    operation_summary="Delete a FAQ (Admin only)",
    tags=['FAQ']
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def faq_delete(request, pk):
    try:
        faq = FAQ.objects.get(pk=pk)
    except FAQ.DoesNotExist:
        return Response({'error': 'FAQ not found.'}, status=status.HTTP_404_NOT_FOUND)
    faq.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)