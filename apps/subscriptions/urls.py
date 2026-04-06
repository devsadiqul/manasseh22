from django.urls import path
from . import views


# Create your urls here.
urlpatterns = [
    path("subscription/", views.SubscriptionView.as_view(), name="subscription"),
    path("subscription/upgrade/", views.UpgradeToPremiumView.as_view(), name="subscription-upgrade"),
    path("subscription/manage/", views.ManageSubscriptionView.as_view(), name="subscription-manage"),
    path("reviews/", views.ReviewView.as_view(), name="reviews"),
]