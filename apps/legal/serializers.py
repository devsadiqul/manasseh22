from rest_framework import serializers
from .models import Legal


# Write your serializers here.
class LegalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Legal
        fields = ['id', 'document_type', 'title', 'content', 'version', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['version', 'created_at', 'updated_at']