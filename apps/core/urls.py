from django.urls import path
from . import views


urlpatterns = [
    # Contact
    path('contact/', views.send_message, name='send-message'),

    # FAQ Category
    path('faq/categories/', views.faq_category_list, name='faq-category-list'),
    path('faq/categories/create/', views.faq_category_create, name='faq-category-create'),
    path('faq/categories/<int:pk>/update/', views.faq_category_update, name='faq-category-update'),
    path('faq/categories/<int:pk>/delete/', views.faq_category_delete, name='faq-category-delete'),

    # FAQ
    path('faqs/', views.faq_list, name='faq-list'),
    path('faqs/create/', views.faq_create, name='faq-create'),
    path('faqs/<int:pk>/', views.faq_detail, name='faq-detail'),
    path('faqs/<int:pk>/update/', views.faq_update, name='faq-update'),
    path('faqs/<int:pk>/delete/', views.faq_delete, name='faq-delete'),
]