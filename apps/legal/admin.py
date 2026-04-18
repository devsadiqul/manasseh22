from django.contrib import admin
from .models import Legal


# Register your models here.
@admin.register(Legal)
class LegalAdmin(admin.ModelAdmin):
    list_display  = ['document_type', 'title', 'version', 'is_active', 'created_at', 'updated_at']
    list_filter   = ['document_type', 'is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['version', 'created_at', 'updated_at']
    ordering      = ['-created_at']