from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="EventMate API",
        default_version="v1",
        description="Shared event planning — weddings, holidays, anniversaries, and more.",
        contact=openapi.Contact(email="support@eventmate.app"),
    ),
    url='https://sound-mite-exotic.ngrok-free.app/api/v1',
    public=True,
    permission_classes=[AllowAny],
)


urlpatterns = [
    path("admin/", admin.site.urls),

    # Docs
    path("", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),

    # Apps
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.subscriptions.urls")),
    path("api/v1/", include("apps.tasks.urls")),
    path("api/v1/", include("apps.legal.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/dashboard/", include("apps.dashboard.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


admin.site.site_header = "EventMate Admin"
admin.site.site_title = "EventMate Admin Portal"
admin.site.index_title = "Welcome to EventMate Admin Dashboard"