from django.urls import path
from . import views


# Create your urls here.
urlpatterns = [
    path("overview/", views.dashboard_overview, name="dashboard-overview"),
    path("user-growth/", views.user_growth, name="dashboard-user-growth"),

    # Events
    path("events/", views.dashboard_events, name="dashboard-events"),
    path("events/<uuid:event_id>/", views.dashboard_event_detail, name="dashboard-event-detail"),
    path("events/<uuid:event_id>/delete/", views.dashboard_event_delete, name="dashboard-event-delete"),

    # Users
    path("users/", views.dashboard_users, name="dashboard-users"),
    path("users/<uuid:user_id>/", views.dashboard_user_detail, name="dashboard-user-detail"),
    path("users/<uuid:user_id>/toggle-active/", views.dashboard_user_toggle_active, name="dashboard-user-toggle-active"),
    path("users/<uuid:user_id>/delete/", views.dashboard_user_delete, name="dashboard-user-delete"),
]