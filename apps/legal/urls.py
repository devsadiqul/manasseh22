from django.urls import path
from . import views


# Write your URL patterns here.
urlpatterns = [
    path('legal/', views.legal_upsert,  name='legal-upsert'),
    path('legal/detail/', views.legal_detail,  name='legal-detail'),
]