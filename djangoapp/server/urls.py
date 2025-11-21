"""
URLs do app server
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import views_study
from . import views_auth

urlpatterns = [
    # ==================== HEALTH CHECK ====================
    path('health/', views.health_check, name='health_check'),
    
    # ==================== AUTHENTICATION ====================
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views_auth.register_view, name='register'),
    
    # ==================== VIEWS HTML - STUDY ====================
    path('', views_study.dashboard_view, name='dashboard'),
    path('dashboard/', views_study.dashboard_view, name='dashboard_alt'),
    path('upload/', views_study.upload_pdf_view, name='upload_pdf'),
    path('events/', views_study.events_list_view, name='events_list'),
    path('subjects/', views_study.subjects_list_view, name='subjects_list'),
    path('plans/', views_study.study_plans_view, name='study_plans'),
    path('onboarding/', views_study.onboarding_view, name='onboarding'),
    
    # ==================== API STUDY ====================
    # Upload e Planos
    path('api/upload-pdf/', views_study.upload_pdf_api, name='upload_pdf_api'),
    path('api/study-plans/', views_study.study_plans_api, name='study_plans_api'),
    path('api/study-plans/<int:plan_id>/', views_study.study_plan_detail_api, name='study_plan_detail_api'),
    path('api/study-plans/<int:plan_id>/status/', views_study.study_plan_status_api, name='study_plan_status_api'),
    
    # Eventos
    path('api/events/', views_study.events_api, name='events_api'),
    path('api/events/<int:event_id>/toggle-complete/', views_study.event_toggle_complete_api, name='event_toggle_complete_api'),
    
    # Matérias
    path('api/subjects/', views_study.subjects_api, name='subjects_api'),
    
    # Notion
    path('api/notion/connect/', views_study.notion_connect_api, name='notion_connect_api'),
    path('api/notion/status/', views_study.notion_status_api, name='notion_status_api'),
    path('api/notion/disconnect/', views_study.notion_disconnect_api, name='notion_disconnect_api'),
    
    # ==================== API TELEGRAM ====================
    # Geração de código
    path('api/telegram/generate-code/', views.generate_telegram_code, name='generate_telegram_code'),
    
    # QR Code
    path('api/telegram/qr-code/<str:code>/', views.generate_qr_code, name='generate_qr_code'),
    
    # Status e gerenciamento
    path('api/telegram/status/', views.telegram_status, name='telegram_status'),
    path('api/telegram/disconnect/', views.disconnect_telegram, name='disconnect_telegram'),
    path('api/telegram/toggle-notifications/', views.toggle_notifications, name='toggle_notifications'),
    
    # Envio de notificações
    path('api/telegram/send-test/', views.send_test_notification, name='send_test_notification'),
    path('api/telegram/send-notification/', views.send_notification, name='send_notification'),
    
    # ==================== WEBHOOK ====================
    path('webhook/telegram/', views.telegram_webhook, name='telegram_webhook'),
    
    # ==================== VIEWS HTML - TELEGRAM ====================
    path('telegram/integration/', views.telegram_integration_page, name='telegram_integration'),
]

