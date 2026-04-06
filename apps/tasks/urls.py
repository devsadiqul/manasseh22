from django.urls import path
from . import views


# Create your urls here.
urlpatterns = [
    # Groups
    path("groups/", views.GroupListCreateView.as_view(), name="group-list-create"),
    path("groups/<uuid:group_id>/", views.GroupDetailView.as_view(), name="group-detail"),
    path("groups/<uuid:group_id>/members/", views.GroupMemberView.as_view(), name="group-members"),
    path("groups/<uuid:group_id>/members/<uuid:user_id>/", views.RemoveMemberView.as_view(), name="group-remove-member"),

    # Tasks
    path("groups/<uuid:group_id>/tasks/", views.TaskListCreateView.as_view(), name="task-list-create"),
    path("groups/<uuid:group_id>/tasks/<uuid:task_id>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("groups/<uuid:group_id>/tasks/<uuid:task_id>/complete/", views.MarkTaskCompleteView.as_view(), name="task-complete"),
    path("groups/<uuid:group_id>/tasks/<uuid:task_id>/comments/", views.TaskCommentListCreateView.as_view(), name="task-comments"),
]