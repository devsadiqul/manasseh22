from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Legal
from .serializers import LegalSerializer


@swagger_auto_schema(
    method='post',
    request_body=LegalSerializer,
    responses={200: LegalSerializer, 201: LegalSerializer},
    tags=['Legal']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def legal_upsert(request):
    document_type = request.data.get('document_type')

    if not document_type:
        return Response(
            {'detail': 'document_type is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    instance = Legal.objects.filter(document_type=document_type, is_active=True).first()

    if instance:
        serializer = LegalSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer = LegalSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'document_type',
            openapi.IN_QUERY,
            description="privacy_policy | terms_conditions | cookie_policy | disclaimer | data_processing",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={200: LegalSerializer},
    tags=['Legal']

)
@api_view(['GET'])
def legal_detail(request):
    document_type = request.query_params.get('document_type')

    if not document_type:
        return Response(
            {'detail': 'document_type query param is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    instance = Legal.objects.filter(document_type=document_type, is_active=True).first()

    if not instance:
        return Response(
            {'detail': 'No active legal document found for this type.'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = LegalSerializer(instance)
    return Response(serializer.data, status=status.HTTP_200_OK)