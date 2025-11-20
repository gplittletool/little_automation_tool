import asyncio
import json
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from telegram import Update

from .models import UserProfile, TelegramVerificationCode, TelegramNotification
from .services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


# ==================== VIEWS DE API ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_telegram_code(request):
    """
    Gera um código de verificação para conectar conta do Telegram
    
    POST /api/telegram/generate-code/
    Response: { 
        "code": "ABC12345", 
        "expires_at": "2024-10-14T12:00:00Z",
        "deep_link": "https://t.me/bot?start=ABC12345",
        "qr_code_url": "/api/telegram/qr-code/ABC12345/"
    }
    """
    try:
        from django.conf import settings
        
        user = request.user
        
        # Gerar código
        verification = TelegramVerificationCode.generate_code(user)
        
        # Pegar username do bot (se configurado)
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
        
        # Gerar URLs
        deep_link = f"https://t.me/{bot_username}?start={verification.code}" if bot_username else None
        deep_link_mobile = f"tg://resolve?domain={bot_username}&start={verification.code}" if bot_username else None
        qr_code_url = f"/api/telegram/qr-code/{verification.code}/"
        
        return Response({
            'success': True,
            'code': verification.code,
            'expires_at': verification.expires_at.isoformat(),
            'deep_link': deep_link,
            'deep_link_mobile': deep_link_mobile,
            'qr_code_url': qr_code_url,
            'bot_username': bot_username,
            'message': 'Código gerado com sucesso'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erro ao gerar código: {e}")
        return Response({
            'success': False,
            'message': 'Erro ao gerar código de verificação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def telegram_status(request):
    """
    Retorna status da conexão com Telegram
    
    GET /api/telegram/status/
    """
    try:
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        data = {
            'is_connected': profile.is_telegram_connected,
            'telegram_username': profile.telegram_username,
            'notifications_enabled': profile.notifications_enabled,
            'connected_at': profile.telegram_connected_at.isoformat() if profile.telegram_connected_at else None
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao buscar status: {e}")
        return Response({
            'error': 'Erro ao buscar status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_telegram(request):
    """
    Desconecta conta do Telegram
    
    POST /api/telegram/disconnect/
    """
    try:
        user = request.user
        profile = UserProfile.objects.filter(user=user).first()
        
        if not profile or not profile.is_telegram_connected:
            return Response({
                'success': False,
                'message': 'Conta do Telegram não está conectada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile.disconnect_telegram()
        
        return Response({
            'success': True,
            'message': 'Conta do Telegram desconectada com sucesso'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao desconectar Telegram: {e}")
        return Response({
            'success': False,
            'message': 'Erro ao desconectar conta'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_notifications(request):
    """
    Ativa/desativa notificações do Telegram
    
    POST /api/telegram/toggle-notifications/
    Body: { "enabled": true/false }
    """
    try:
        user = request.user
        enabled = request.data.get('enabled', True)
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.notifications_enabled = enabled
        profile.save()
        
        return Response({
            'success': True,
            'notifications_enabled': profile.notifications_enabled,
            'message': f"Notificações {'ativadas' if enabled else 'desativadas'}"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao alterar notificações: {e}")
        return Response({
            'success': False,
            'message': 'Erro ao alterar configuração'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_notification(request):
    """
    Envia uma notificação de teste para o usuário
    
    POST /api/telegram/send-test/
    """
    try:
        user = request.user
        profile = UserProfile.objects.filter(user=user).first()
        
        if not profile or not profile.is_telegram_connected:
            return Response({
                'success': False,
                'message': 'Conta do Telegram não está conectada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Enviar notificação de teste
        title = "🧪 Notificação de Teste"
        message = (
            f"Olá, {user.first_name or user.username}!\n\n"
            "Esta é uma notificação de teste do Sistema de Automação de Estudos.\n\n"
            "✅ Suas notificações estão funcionando perfeitamente!"
        )
        
        # Executar de forma assíncrona
        success = asyncio.run(
            TelegramService.send_notification(profile, title, message)
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'Notificação de teste enviada com sucesso!'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Falha ao enviar notificação'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de teste: {e}")
        return Response({
            'success': False,
            'message': 'Erro ao enviar notificação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_qr_code(request, code):
    """
    Gera QR Code para conexão rápida via Telegram
    
    GET /api/telegram/qr-code/<code>/
    Returns: PNG image
    """
    try:
        from django.conf import settings
        import qrcode
        from io import BytesIO
        
        user = request.user
        
        # Verificar se código pertence ao usuário e é válido
        verification = TelegramVerificationCode.objects.filter(
            code=code.upper(),
            user=user,
            is_used=False
        ).first()
        
        if not verification or not verification.is_valid():
            return HttpResponse("Código inválido ou expirado", status=404)
        
        # Pegar username do bot
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
        
        if not bot_username:
            return HttpResponse("Bot não configurado", status=500)
        
        # Gerar deep link
        deep_link = f"https://t.me/{bot_username}?start={code.upper()}"
        
        # Gerar QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(deep_link)
        qr.make(fit=True)
        
        # Criar imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Salvar em buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Retornar imagem
        return HttpResponse(buffer.getvalue(), content_type='image/png')
        
    except Exception as e:
        logger.error(f"Erro ao gerar QR Code: {e}")
        return HttpResponse("Erro ao gerar QR Code", status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_notification(request):
    """
    Envia uma notificação customizada para o usuário
    
    POST /api/telegram/send-notification/
    Body: {
        "title": "Título da notificação",
        "message": "Conteúdo da mensagem",
        "event_data": { ... } (opcional)
    }
    """
    try:
        user = request.user
        profile = UserProfile.objects.filter(user=user).first()
        
        if not profile or not profile.is_telegram_connected:
            return Response({
                'success': False,
                'message': 'Conta do Telegram não está conectada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar dados
        title = request.data.get('title')
        message = request.data.get('message')
        event_data = request.data.get('event_data', {})
        
        if not title or not message:
            return Response({
                'success': False,
                'message': 'Título e mensagem são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar registro de notificação
        notification = TelegramNotification.objects.create(
            user=user,
            message_title=title,
            message_text=message,
            status='pending'
        )
        
        # Formatar e enviar
        formatted_message = TelegramService.format_notification(title, message, event_data)
        
        success = asyncio.run(
            TelegramService.send_notification(profile, title, formatted_message, notification)
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'Notificação enviada com sucesso!',
                'notification_id': notification.id
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Falha ao enviar notificação'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação: {e}")
        return Response({
            'success': False,
            'message': 'Erro ao enviar notificação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== WEBHOOK DO TELEGRAM ====================

@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """
    Webhook para receber atualizações do Telegram
    
    POST /webhook/telegram/
    """
    try:
        # Parse do JSON
        data = json.loads(request.body.decode('utf-8'))
        
        # Criar objeto Update
        update = Update.de_json(data, TelegramService.get_bot())
        
        # Processar update de forma assíncrona
        application = TelegramService.get_application()
        asyncio.run(application.process_update(update))
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Erro no webhook do Telegram: {e}")
        return HttpResponse("Error", status=500)


# ==================== VIEWS HTML (Opcional - para futuro) ====================

@login_required
def telegram_integration_page(request):
    """
    Página de integração com Telegram
    """
    from django.conf import settings
    
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Buscar código ativo se existir
    active_code = TelegramVerificationCode.objects.filter(
        user=user,
        is_used=False,
        expires_at__gt=timezone.now()
    ).first()
    
    # Username do bot
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
    
    context = {
        'profile': profile,
        'active_code': active_code,
        'bot_username': bot_username,
    }
    
    return render(request, 'telegram/integration.html', context)
