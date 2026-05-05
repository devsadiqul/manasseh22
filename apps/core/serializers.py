from rest_framework import serializers
from .models import FAQCategory, FAQ
 
 
# Create your serializers
class FAQSerializer(serializers.ModelSerializer):

    class Meta:
        model = FAQ
        fields = [
            'id', 'category', 'question', 'answer', 'order',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        category = attrs.get('category', getattr(self.instance, 'category', None))
        order = attrs.get('order', getattr(self.instance, 'order', None))

        qs = FAQ.objects.filter(category=category, order=order)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({
                'order': 'This order is already used in this category.'
            })
        return attrs


class FAQCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = FAQCategory
        fields = [
            'id', 'name', 'order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_order(self, value):
        qs = FAQCategory.objects.filter(order=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'This order is already used by another category.'
            )
        return value
 
 
class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()