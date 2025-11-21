"""
Views para Upload de PDF, Processamento e Exibição de Eventos
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, F
from django.db import models
from django.utils import timezone
from datetime import timedelta

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from .models import UserProfile, StudyPlan, StudyEvent, Subject
from .serializers import (
    StudyPlanListSerializer, StudyPlanDetailSerializer, StudyPlanUploadSerializer,
    StudyEventSerializer, SubjectSerializer
)
from .tasks import process_study_plan
from .services.notion_service import NotionService

logger = logging.getLogger(__name__)


# ==================== VIEWS HTML ====================

@login_required
def dashboard_view(request):
    """Dashboard principal do usuário"""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    # Estatísticas
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    total_subjects = Subject.objects.filter(user=user, is_active=True).count()
    total_events = StudyEvent.objects.filter(study_plan__user=user).count()
    
    # Eventos próximos
    upcoming_events = StudyEvent.objects.filter(
        study_plan__user=user,
        event_date__gte=today,
        is_completed=False
    ).order_by('event_date', 'event_time')[:5]
    
    # Eventos hoje
    today_events = StudyEvent.objects.filter(
        study_plan__user=user,
        event_date=today,
        is_completed=False
    ).count()
    
    # Eventos esta semana
    week_events = StudyEvent.objects.filter(
        study_plan__user=user,
        event_date__range=[today, next_week],
        is_completed=False
    ).count()
    
    # Matérias em risco (alta taxa de falta)
    at_risk_subjects = Subject.objects.filter(
        user=user,
        is_active=True
    ).filter(
        current_absences__gte=models.F('max_absences') * 0.75
    )[:3]
    
    # Planos recentes
    recent_plans = StudyPlan.objects.filter(user=user).order_by('-created_at')[:3]
    
    context = {
        'profile': profile,
        'total_subjects': total_subjects,
        'total_events': total_events,
        'today_events': today_events,
        'week_events': week_events,
        'upcoming_events': upcoming_events,
        'at_risk_subjects': at_risk_subjects,
        'recent_plans': recent_plans,
    }
    
    return render(request, 'study/dashboard.html', context)


@login_required
def upload_pdf_view(request):
    """Página de upload de PDF"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'study/upload_pdf.html', context)


@login_required
def events_list_view(request):
    """Lista de eventos do usuário"""
    user = request.user
    
    # Filtros
    filter_type = request.GET.get('type', 'all')
    filter_subject = request.GET.get('subject')
    filter_date = request.GET.get('date', 'upcoming')
    
    today = timezone.now().date()
    
    # Query base
    events = StudyEvent.objects.filter(study_plan__user=user).select_related('subject', 'study_plan')
    
    # Aplicar filtros
    if filter_date == 'upcoming':
        events = events.filter(event_date__gte=today, is_completed=False)
    elif filter_date == 'past':
        events = events.filter(Q(event_date__lt=today) | Q(is_completed=True))
    elif filter_date == 'today':
        events = events.filter(event_date=today)
    elif filter_date == 'week':
        next_week = today + timedelta(days=7)
        events = events.filter(event_date__range=[today, next_week], is_completed=False)
    
    if filter_type and filter_type != 'all':
        events = events.filter(event_type=filter_type)
    
    if filter_subject:
        events = events.filter(subject_id=filter_subject)
    
    events = events.order_by('event_date', 'event_time')
    
    # Subjects para filtro
    subjects = Subject.objects.filter(user=user, is_active=True).order_by('name')
    
    context = {
        'events': events,
        'subjects': subjects,
        'filter_type': filter_type,
        'filter_date': filter_date,
        'filter_subject': filter_subject,
        'event_types': StudyEvent.EVENT_TYPES,
    }
    
    return render(request, 'study/events_list.html', context)


@login_required
def subjects_list_view(request):
    """Lista de matérias do usuário"""
    user = request.user
    subjects = Subject.objects.filter(user=user).order_by('-is_active', 'name')
    
    context = {
        'subjects': subjects,
    }
    
    return render(request, 'study/subjects_list.html', context)


@login_required
def study_plans_view(request):
    """Lista de planos de estudo"""
    user = request.user
    plans = StudyPlan.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'plans': plans,
    }
    
    return render(request, 'study/study_plans.html', context)


@login_required
def onboarding_view(request):
    """Página de onboarding para conectar Telegram e Notion"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'study/onboarding.html', context)


# ==================== API ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_pdf_api(request):
    """
    Upload de PDF para processar
    
    POST /api/upload-pdf/
    Content-Type: multipart/form-data
    Body: {
        "title": "Plano 2025.1",
        "description": "Calendário acadêmico",
        "pdf_file": <file>
    }
    """
    try:
        logger.info(f"[UPLOAD] Recebendo upload de PDF do usuário: {request.user.username}")
        
        serializer = StudyPlanUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"[UPLOAD] Erro de validação: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar StudyPlan
        study_plan = serializer.save(user=request.user)
        logger.info(f"[UPLOAD] StudyPlan criado com sucesso: ID={study_plan.id}, Título={study_plan.title}")
        
        # Disparar task Celery para processar
        task_result = process_study_plan.delay(study_plan.id)
        logger.info(f"[UPLOAD] Task Celery disparada: task_id={task_result.id}, study_plan_id={study_plan.id}")
        
        logger.info(f"[UPLOAD] Upload completo para: {study_plan.id} - {study_plan.title}")
        
        return Response({
            'success': True,
            'study_plan_id': study_plan.id,
            'title': study_plan.title,
            'status': study_plan.status,
            'message': 'PDF enviado com sucesso! Processamento iniciado.'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erro ao fazer upload: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def study_plans_api(request):
    """
    Lista planos de estudo do usuário
    
    GET /api/study-plans/
    """
    plans = StudyPlan.objects.filter(user=request.user).order_by('-created_at')
    serializer = StudyPlanListSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def study_plan_detail_api(request, plan_id):
    """
    Detalhes de um plano específico
    
    GET /api/study-plans/<id>/
    """
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    serializer = StudyPlanDetailSerializer(plan)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def study_plan_status_api(request, plan_id):
    """
    Verifica status do processamento
    
    GET /api/study-plans/<id>/status/
    """
    plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
    
    return Response({
        'id': plan.id,
        'status': plan.status,
        'events_created': plan.events_created,
        'subjects_created': plan.subjects_created,
        'error_message': plan.error_message,
        'processed_at': plan.processed_at.isoformat() if plan.processed_at else None
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def events_api(request):
    """
    Lista eventos do usuário
    
    GET /api/events/
    Query params:
      - type: prova, trabalho, etc
      - date: upcoming, past, today, week
      - subject: ID da matéria
    """
    user = request.user
    today = timezone.now().date()
    
    events = StudyEvent.objects.filter(study_plan__user=user)
    
    # Filtros
    event_type = request.GET.get('type')
    date_filter = request.GET.get('date', 'upcoming')
    subject_id = request.GET.get('subject')
    
    if event_type:
        events = events.filter(event_type=event_type)
    
    if date_filter == 'upcoming':
        events = events.filter(event_date__gte=today, is_completed=False)
    elif date_filter == 'past':
        events = events.filter(Q(event_date__lt=today) | Q(is_completed=True))
    elif date_filter == 'today':
        events = events.filter(event_date=today)
    elif date_filter == 'week':
        next_week = today + timedelta(days=7)
        events = events.filter(event_date__range=[today, next_week], is_completed=False)
    
    if subject_id:
        events = events.filter(subject_id=subject_id)
    
    events = events.order_by('event_date', 'event_time')
    
    serializer = StudyEventSerializer(events, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def event_toggle_complete_api(request, event_id):
    """
    Marca evento como concluído/não concluído
    
    PATCH /api/events/<id>/toggle-complete/
    """
    event = get_object_or_404(StudyEvent, id=event_id, study_plan__user=request.user)
    
    event.is_completed = not event.is_completed
    event.completed_at = timezone.now() if event.is_completed else None
    event.save()
    
    return Response({
        'success': True,
        'is_completed': event.is_completed,
        'completed_at': event.completed_at.isoformat() if event.completed_at else None
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subjects_api(request):
    """
    Lista matérias do usuário
    
    GET /api/subjects/
    """
    subjects = Subject.objects.filter(user=request.user, is_active=True).order_by('name')
    serializer = SubjectSerializer(subjects, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notion_connect_api(request):
    """
    Conecta conta do Notion
    
    POST /api/notion/connect/
    Body: {
        "token": "secret_...",
        "database_id": "abc123..."
    }
    """
    try:
        token = request.data.get('token')
        database_id = request.data.get('database_id')
        
        if not token or not database_id:
            return Response({
                'success': False,
                'message': 'Token e Database ID são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar conexão
        notion_service = NotionService(token, database_id)
        is_valid, message = notion_service.validate_connection()
        
        if not is_valid:
            return Response({
                'success': False,
                'message': f'Erro ao conectar com Notion: {message}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Salvar no perfil
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.notion_token = token
        profile.notion_database_id = database_id
        profile.is_notion_connected = True
        profile.notion_connected_at = timezone.now()
        profile.save()
        
        logger.info(f"Notion conectado para usuário {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Notion conectado com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao conectar Notion: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notion_status_api(request):
    """
    Verifica status da conexão Notion
    
    GET /api/notion/status/
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    return Response({
        'is_connected': profile.is_notion_connected,
        'connected_at': profile.notion_connected_at.isoformat() if profile.notion_connected_at else None
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notion_disconnect_api(request):
    """
    Desconecta Notion
    
    POST /api/notion/disconnect/
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    profile.disconnect_notion()
    
    return Response({
        'success': True,
        'message': 'Notion desconectado'
    })

