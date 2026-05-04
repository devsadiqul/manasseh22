from django.urls import path
from . import views


# Create your urls here.
urlpatterns = [
    # Events
    path("events/", views.event_list, name="event-list"),
    path("events/create/", views.event_create, name="event-create"),
    path("events/<uuid:event_id>/", views.event_details, name="event-details"),
    path("events/<uuid:event_id>/update/", views.event_update, name="event-update"),
    path("events/<uuid:event_id>/delete/", views.event_delete, name="event-delete"),

    # Event Members
    path("events/<uuid:event_id>/members/", views.event_member_list, name="event-member-list"),
    path("events/<uuid:event_id>/members/add/", views.event_member_add, name="event-member-add"),
    path("events/<uuid:event_id>/members/<int:member_id>/remove/", views.event_member_remove, name="event-member-remove"),
    path("events/<uuid:event_id>/invite-link/", views.event_invite_link, name="event-invite-link"),
    path("events/join/<uuid:token>/", views.event_join_by_invite, name="event-join-by-invite"),

    # Tasks
    path("tasks/my/", views.my_task_list, name="my-task-list"),
    path("events/<uuid:event_id>/tasks/", views.task_list, name="task-list"),
    path("events/<uuid:event_id>/tasks/create/", views.task_create, name="task-create"),
    path("events/<uuid:event_id>/tasks/<uuid:task_id>/", views.task_details, name="task-details"),
    path("events/<uuid:event_id>/tasks/<uuid:task_id>/update/", views.task_update, name="task-update"),
    path("events/<uuid:event_id>/tasks/<uuid:task_id>/delete/", views.task_delete, name="task-delete"),
    path("events/<uuid:event_id>/tasks/<uuid:task_id>/complete/", views.task_mark_complete, name="task-mark-complete"),

    # Task Comments
    path("events/<uuid:event_id>/tasks/<uuid:task_id>/comments/", views.task_comment_list, name="task-comment-list"),
    path("events/<uuid:event_id>/tasks/<uuid:task_id>/comments/create/", views.task_comment_create, name="task-comment-create"),
]