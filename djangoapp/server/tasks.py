"""
Celery tasks para processamento assíncrono
"""
import logging
from datetime import datetime
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone
from dateutil import parser as date_parser

from .models import StudyPlan, Subject, StudyEvent, UserProfile, TelegramNotification
from .services.pdf_processor import PDFProcessor
from .services.ai_service import AIService
from .services.notion_service import NotionService
from .services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_study_plan(self, study_plan_id: int):
    """
    Processa um plano de estudos completo
    
    Fluxo:
    1. Extrai texto do PDF
    2. Envia para IA analisar
    3. Cria matérias e eventos no banco
    4. Sincroniza com Notion (se conectado)
    5. Notifica usuário no Telegram
    
    Args:
        study_plan_id: ID do StudyPlan
    """
    try:
        # Buscar plano
        study_plan = StudyPlan.objects.get(id=study_plan_id)
        user = study_plan.user
        
        logger.info(f"Iniciando processamento do plano {study_plan_id}")
        
        # 1. Atualizar status
        study_plan.status = 'processing'
        study_plan.save()
        
        # 2. Extrair texto do PDF
        logger.info("Extraindo texto do PDF...")
        pdf_text = PDFProcessor.extract_text(study_plan.pdf_file.path)
        
        if not pdf_text:
            raise Exception("Não foi possível extrair texto do PDF")
        
        # 3. Analisar com IA
        logger.info("Analisando com IA...")
        ai_result = AIService.analyze_study_plan(pdf_text)
        
        if not ai_result:
            raise Exception("Falha na análise com IA")
        
        # Salvar resultado bruto
        study_plan.ai_raw_response = ai_result['raw_response']
        study_plan.ai_analysis = ai_result['analysis']
        study_plan.save()
        
        analysis = ai_result['analysis']
        
        # 4. Criar matérias
        logger.info("Criando matérias...")
        subjects_created = _create_subjects(user, analysis.get('subjects', []), analysis.get('period', ''))
        study_plan.subjects_created = len(subjects_created)
        
        # 5. Criar eventos
        logger.info("Criando eventos...")
        events_created = _create_events(study_plan, analysis.get('events', []), subjects_created)
        study_plan.events_created = len(events_created)
        
        # 6. Sincronizar com Notion (se configurado)
        profile = UserProfile.objects.filter(user=user).first()
        if profile and hasattr(profile, 'notion_token') and profile.notion_token:
            logger.info("Sincronizando com Notion...")
            _sync_to_notion(profile, events_created)
            study_plan.synced_to_notion = True
            study_plan.synced_at = timezone.now()
        
        # 7. Finalizar
        study_plan.status = 'completed'
        study_plan.processed_at = timezone.now()
        study_plan.save()
        
        logger.info(f"Processamento concluído: {len(subjects_created)} matérias, {len(events_created)} eventos")
        
        # 8. Notificar usuário no Telegram
        _notify_user_completion(user, study_plan, len(subjects_created), len(events_created))
        
        return {
            'success': True,
            'subjects_created': len(subjects_created),
            'events_created': len(events_created)
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar plano {study_plan_id}: {e}")
        
        # Atualizar status de erro
        study_plan.status = 'failed'
        study_plan.error_message = str(e)
        study_plan.save()
        
        # Notificar usuário do erro
        _notify_user_error(study_plan.user, str(e))
        
        raise


def _create_subjects(user, subjects_data: list, semester: str) -> Dict[str, Subject]:
    """Cria matérias no banco"""
    created = {}
    
    for subject_data in subjects_data:
        name = subject_data.get('name')
        if not name:
            continue
        
        # Criar ou atualizar matéria
        subject, created_new = Subject.objects.get_or_create(
            user=user,
            name=name,
            semester=semester,
            defaults={
                'code': subject_data.get('code', ''),
                'professor': subject_data.get('professor', ''),
                'total_classes': subject_data.get('total_hours', 0) // 2,  # Estimativa
                'max_absences': subject_data.get('max_absences', 0),
                'schedule_info': subject_data.get('schedule', {}),
            }
        )
        
        created[name] = subject
        logger.info(f"Matéria {'criada' if created_new else 'encontrada'}: {name}")
    
    return created


def _create_events(study_plan: StudyPlan, events_data: list, subjects_map: Dict[str, Subject]) -> list:
    """Cria eventos no banco"""
    created = []
    
    for event_data in events_data:
        try:
            # Parse da data
            date_str = event_data.get('date')
            if not date_str:
                continue
            
            try:
                event_date = date_parser.parse(date_str).date()
            except:
                logger.warning(f"Data inválida: {date_str}")
                continue
            
            # Parse do horário
            event_time = None
            time_str = event_data.get('time')
            if time_str:
                try:
                    event_time = date_parser.parse(time_str).time()
                except:
                    pass
            
            # Buscar matéria
            subject = None
            subject_name = event_data.get('subject')
            if subject_name and subject_name in subjects_map:
                subject = subjects_map[subject_name]
            
            # Criar evento
            event = StudyEvent.objects.create(
                study_plan=study_plan,
                subject=subject,
                title=event_data.get('title', 'Evento sem título'),
                description=event_data.get('description', ''),
                event_type=event_data.get('event_type', 'outro'),
                event_date=event_date,
                event_time=event_time,
                location=event_data.get('location', ''),
                priority=event_data.get('priority', 3)
            )
            
            created.append(event)
            logger.info(f"Evento criado: {event.title} em {event_date}")
            
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            continue
    
    return created


def _sync_to_notion(profile: UserProfile, events: list):
    """Sincroniza eventos com Notion"""
    # Esta função será implementada quando adicionar campos de Notion no UserProfile
    pass


def _notify_user_completion(user, study_plan: StudyPlan, subjects_count: int, events_count: int):
    """Notifica usuário que processamento foi concluído"""
    try:
        profile = UserProfile.objects.filter(user=user, is_telegram_connected=True).first()
        if not profile:
            return
        
        title = "✅ Plano de Estudos Processado!"
        message = (
            f"Seu plano '{study_plan.title}' foi processado com sucesso!\n\n"
            f"📚 Matérias identificadas: {subjects_count}\n"
            f"📅 Eventos criados: {events_count}\n\n"
            f"Acesse o sistema para visualizar todos os detalhes."
        )
        
        # Enviar via Celery task
        send_telegram_notification.delay(profile.id, title, message)
        
    except Exception as e:
        logger.error(f"Erro ao notificar usuário: {e}")


def _notify_user_error(user, error_message: str):
    """Notifica usuário de erro no processamento"""
    try:
        profile = UserProfile.objects.filter(user=user, is_telegram_connected=True).first()
        if not profile:
            return
        
        title = "❌ Erro no Processamento"
        message = (
            f"Ocorreu um erro ao processar seu plano de estudos:\n\n"
            f"{error_message}\n\n"
            f"Por favor, tente novamente ou entre em contato com o suporte."
        )
        
        send_telegram_notification.delay(profile.id, title, message)
        
    except Exception as e:
        logger.error(f"Erro ao notificar erro: {e}")


@shared_task
def send_telegram_notification(profile_id: int, title: str, message: str):
    """
    Envia notificação via Telegram
    
    Args:
        profile_id: ID do UserProfile
        title: Título da notificação
        message: Conteúdo
    """
    try:
        import asyncio
        
        profile = UserProfile.objects.get(id=profile_id)
        
        if not profile.is_telegram_connected:
            logger.warning(f"Perfil {profile_id} não tem Telegram conectado")
            return
        
        # Criar registro de notificação
        notification = TelegramNotification.objects.create(
            user=profile.user,
            message_title=title,
            message_text=message,
            status='pending'
        )
        
        # Enviar
        success = asyncio.run(
            TelegramService.send_notification(profile, title, message, notification)
        )
        
        return {'success': success, 'notification_id': notification.id}
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação Telegram: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def check_upcoming_events():
    """
    Task periódica para verificar eventos próximos e enviar lembretes
    
    Deve rodar a cada hora via Celery Beat
    """
    from datetime import timedelta
    
    logger.info("Verificando eventos próximos...")
    
    now = timezone.now()
    tomorrow = now + timedelta(days=1)
    in_3_hours = now + timedelta(hours=3)
    
    # Eventos amanhã (que ainda não foram notificados)
    events_tomorrow = StudyEvent.objects.filter(
        event_date=tomorrow.date(),
        is_completed=False,
        notification_sent_1d=False
    ).select_related('study_plan__user', 'subject')
    
    for event in events_tomorrow:
        _send_event_reminder(event, "1 dia")
        event.notification_sent_1d = True
        event.save()
    
    # Eventos em 3 horas (que ainda não foram notificados)
    events_3h = StudyEvent.objects.filter(
        event_date=now.date(),
        is_completed=False,
        notification_sent_3h=False
    ).select_related('study_plan__user', 'subject')
    
    for event in events_3h:
        if event.event_time:
            event_datetime = datetime.combine(event.event_date, event.event_time)
            event_datetime = timezone.make_aware(event_datetime)
            
            if event_datetime <= in_3_hours:
                _send_event_reminder(event, "3 horas")
                event.notification_sent_3h = True
                event.save()
    
    logger.info(f"Verificação concluída: {len(events_tomorrow)} lembretes de 1 dia, eventos 3h processados")


def _send_event_reminder(event: StudyEvent, timeframe: str):
    """Envia lembrete de evento"""
    try:
        user = event.study_plan.user
        profile = UserProfile.objects.filter(user=user, is_telegram_connected=True).first()
        
        if not profile or not profile.notifications_enabled:
            return
        
        # Formatar mensagem
        type_emoji = {
            'prova': '📝',
            'trabalho': '📄',
            'entrega': '📤',
            'revisao': '📖',
            'aula': '🎓',
            'outro': '📚'
        }.get(event.event_type, '📅')
        
        title = f"{type_emoji} Lembrete: {event.title}"
        
        message = f"Você tem um evento daqui a {timeframe}!\n\n"
        message += f"📅 Data: {event.event_date.strftime('%d/%m/%Y')}\n"
        
        if event.event_time:
            message += f"⏰ Horário: {event.event_time.strftime('%H:%M')}\n"
        
        if event.subject:
            message += f"📚 Matéria: {event.subject.name}\n"
        
        if event.location:
            message += f"📍 Local: {event.location}\n"
        
        if event.description:
            message += f"\n💡 {event.description}\n"
        
        # Enviar
        send_telegram_notification.delay(profile.id, title, message)
        
    except Exception as e:
        logger.error(f"Erro ao enviar lembrete: {e}")

