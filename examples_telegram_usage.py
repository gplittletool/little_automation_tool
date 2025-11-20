"""
Exemplos de uso da API de notificações Telegram

Este arquivo demonstra como usar a integração do Telegram
de forma programática no Django.
"""

# ==================== EXEMPLO 1: Enviar Notificação Simples ====================

def enviar_notificacao_simples(user):
    """
    Envia uma notificação simples para um usuário
    """
    from server.services.telegram_service import TelegramService
    from server.models import UserProfile
    import asyncio
    
    # Buscar perfil do usuário
    try:
        profile = UserProfile.objects.get(user=user, is_telegram_connected=True)
    except UserProfile.DoesNotExist:
        print(f"Usuário {user.username} não tem Telegram conectado")
        return False
    
    # Enviar notificação
    success = asyncio.run(
        TelegramService.send_notification(
            user_profile=profile,
            title="🎓 Lembrete de Estudo",
            message="Você tem uma prova de Cálculo I amanhã às 09:00!"
        )
    )
    
    return success


# ==================== EXEMPLO 2: Notificação com Dados do Evento ====================

def enviar_lembrete_prova(user, prova_data):
    """
    Envia notificação de prova com dados formatados
    
    Args:
        user: Django User object
        prova_data: Dict com dados da prova
            {
                'materia': 'Cálculo I',
                'data': '14/10/2025',
                'horario': '09:00',
                'sala': 'Lab 301',
                'topicos': ['Derivadas', 'Integrais']
            }
    """
    from server.services.telegram_service import TelegramService
    from server.models import UserProfile
    import asyncio
    
    profile = UserProfile.objects.get(user=user, is_telegram_connected=True)
    
    # Formatar mensagem
    title = f"📝 Prova de {prova_data['materia']}"
    
    message = (
        f"Você tem uma prova amanhã!\n\n"
        f"📚 Conteúdo: {', '.join(prova_data['topicos'])}\n"
        f"🎯 Revise bem esses tópicos!"
    )
    
    # Dados extras para formatação
    event_data = {
        'date': prova_data['data'],
        'time': prova_data['horario'],
        'location': prova_data['sala'],
        'subject': prova_data['materia']
    }
    
    # Formatar com template
    formatted_message = TelegramService.format_notification(title, message, event_data)
    
    # Enviar
    success = asyncio.run(
        TelegramService.send_notification(profile, title, formatted_message)
    )
    
    return success


# ==================== EXEMPLO 3: Notificar Múltiplos Usuários ====================

def notificar_todos_usuarios(titulo, mensagem):
    """
    Envia notificação para todos os usuários com Telegram conectado
    """
    from server.models import UserProfile, TelegramNotification
    from server.services.telegram_service import TelegramService
    import asyncio
    
    # Buscar todos os perfis conectados e com notificações ativas
    profiles = UserProfile.objects.filter(
        is_telegram_connected=True,
        notifications_enabled=True
    )
    
    resultados = {
        'sucesso': 0,
        'falha': 0,
        'total': profiles.count()
    }
    
    for profile in profiles:
        # Criar registro de notificação
        notification = TelegramNotification.objects.create(
            user=profile.user,
            message_title=titulo,
            message_text=mensagem,
            status='pending'
        )
        
        # Tentar enviar
        success = asyncio.run(
            TelegramService.send_notification(
                profile, titulo, mensagem, notification
            )
        )
        
        if success:
            resultados['sucesso'] += 1
        else:
            resultados['falha'] += 1
    
    return resultados


# ==================== EXEMPLO 4: Gerar Código e Aguardar Conexão ====================

def processo_completo_conexao(user):
    """
    Demonstra o fluxo completo de conexão do Telegram
    """
    from server.models import TelegramVerificationCode, UserProfile
    
    # 1. Gerar código
    code = TelegramVerificationCode.generate_code(user, validity_hours=24)
    print(f"Código gerado: {code.code}")
    print(f"Expira em: {code.expires_at}")
    print(f"\nInstruções para o usuário:")
    print(f"1. Abra o Telegram")
    print(f"2. Busque: @seu_bot_username")
    print(f"3. Envie: /start")
    print(f"4. Envie: /verificar {code.code}")
    
    # 2. Verificar se foi conectado (em outro momento)
    # Este código seria executado depois que o usuário conectou
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if profile.is_telegram_connected:
        print(f"\n✅ Conta conectada!")
        print(f"Username: @{profile.telegram_username}")
        print(f"Conectado em: {profile.telegram_connected_at}")
        return True
    else:
        print(f"\n⏳ Aguardando conexão...")
        return False


# ==================== EXEMPLO 5: Notificação de Falta Próxima do Limite ====================

def alertar_limite_faltas(user, materia, faltas_atuais, limite):
    """
    Alerta quando usuário está próximo do limite de faltas
    """
    from server.services.telegram_service import TelegramService
    from server.models import UserProfile
    import asyncio
    
    profile = UserProfile.objects.get(user=user, is_telegram_connected=True)
    
    faltas_restantes = limite - faltas_atuais
    percentual = (faltas_atuais / limite) * 100
    
    # Emoji baseado na gravidade
    if percentual >= 90:
        emoji = "🔴"
        urgencia = "CRÍTICO"
    elif percentual >= 75:
        emoji = "🟠"
        urgencia = "ALERTA"
    else:
        emoji = "🟡"
        urgencia = "ATENÇÃO"
    
    title = f"{emoji} {urgencia}: Limite de Faltas"
    
    message = (
        f"Matéria: {materia}\n\n"
        f"Faltas: {faltas_atuais} de {limite}\n"
        f"Restam apenas: {faltas_restantes} faltas\n"
        f"Percentual: {percentual:.1f}%\n\n"
        f"⚠️ Cuidado para não reprovar por falta!"
    )
    
    success = asyncio.run(
        TelegramService.send_notification(profile, title, message)
    )
    
    return success


# ==================== EXEMPLO 6: Usar em Django View ====================

def exemplo_view_api(request):
    """
    Exemplo de como usar em uma view Django
    """
    from rest_framework.decorators import api_view, permission_classes
    from rest_framework.permissions import IsAuthenticated
    from rest_framework.response import Response
    from server.services.telegram_service import TelegramService
    from server.models import UserProfile
    import asyncio
    
    @api_view(['POST'])
    @permission_classes([IsAuthenticated])
    def enviar_lembrete_personalizado(request):
        """
        POST /api/lembrete/
        Body: {
            "titulo": "Título do lembrete",
            "mensagem": "Conteúdo",
            "dados_evento": {...}
        }
        """
        user = request.user
        
        # Verificar se tem Telegram conectado
        try:
            profile = UserProfile.objects.get(user=user, is_telegram_connected=True)
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Telegram não conectado'
            }, status=400)
        
        # Dados da requisição
        titulo = request.data.get('titulo')
        mensagem = request.data.get('mensagem')
        dados_evento = request.data.get('dados_evento', {})
        
        # Formatar e enviar
        formatted = TelegramService.format_notification(titulo, mensagem, dados_evento)
        success = asyncio.run(
            TelegramService.send_notification(profile, titulo, formatted)
        )
        
        if success:
            return Response({'message': 'Notificação enviada!'})
        else:
            return Response({'error': 'Falha ao enviar'}, status=500)
    
    return enviar_lembrete_personalizado


# ==================== EXEMPLO 7: Notificação Agendada (com Celery - futuro) ====================

def exemplo_task_celery():
    """
    Exemplo de task Celery para notificações agendadas
    
    Obs: Requer Celery instalado e configurado
    """
    from celery import shared_task
    from server.models import UserProfile
    from server.services.telegram_service import TelegramService
    import asyncio
    
    @shared_task
    def enviar_lembretes_diarios():
        """
        Task executada diariamente para enviar lembretes
        """
        from django.utils import timezone
        from datetime import timedelta
        
        amanha = timezone.now().date() + timedelta(days=1)
        
        # Buscar eventos de amanhã (exemplo - adaptar ao seu model)
        # eventos = StudyEvent.objects.filter(event_date=amanha)
        
        profiles = UserProfile.objects.filter(
            is_telegram_connected=True,
            notifications_enabled=True
        )
        
        for profile in profiles:
            # eventos_usuario = eventos.filter(study_plan__user=profile.user)
            
            # if eventos_usuario.exists():
            message = f"Você tem eventos agendados para amanhã!"
            
            asyncio.run(
                TelegramService.send_notification(
                    profile,
                    "📅 Lembretes de Amanhã",
                    message
                )
            )
        
        return f"Lembretes enviados para {profiles.count()} usuários"


# ==================== EXEMPLO 8: Verificar Status Antes de Enviar ====================

def enviar_com_verificacao(user, titulo, mensagem):
    """
    Verifica todas as condições antes de enviar notificação
    """
    from server.models import UserProfile
    from server.services.telegram_service import TelegramService
    import asyncio
    
    # 1. Verificar se perfil existe
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return {
            'success': False,
            'error': 'Perfil não existe'
        }
    
    # 2. Verificar se Telegram está conectado
    if not profile.is_telegram_connected:
        return {
            'success': False,
            'error': 'Telegram não conectado'
        }
    
    # 3. Verificar se notificações estão habilitadas
    if not profile.notifications_enabled:
        return {
            'success': False,
            'error': 'Notificações desabilitadas pelo usuário'
        }
    
    # 4. Tentar enviar
    try:
        success = asyncio.run(
            TelegramService.send_notification(profile, titulo, mensagem)
        )
        
        if success:
            return {
                'success': True,
                'message': 'Notificação enviada com sucesso'
            }
        else:
            return {
                'success': False,
                'error': 'Falha ao enviar via Telegram API'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Erro inesperado: {str(e)}'
        }


# ==================== COMO USAR ESTES EXEMPLOS ====================

if __name__ == "__main__":
    """
    Para testar estes exemplos no Django shell:
    
    python manage.py shell
    
    >>> from django.contrib.auth.models import User
    >>> from examples_telegram_usage import *
    >>> 
    >>> # Exemplo 1: Notificação simples
    >>> user = User.objects.get(username='seu_usuario')
    >>> enviar_notificacao_simples(user)
    >>> 
    >>> # Exemplo 2: Notificação de prova
    >>> prova = {
    >>>     'materia': 'Cálculo I',
    >>>     'data': '14/10/2025',
    >>>     'horario': '09:00',
    >>>     'sala': 'Lab 301',
    >>>     'topicos': ['Derivadas', 'Integrais']
    >>> }
    >>> enviar_lembrete_prova(user, prova)
    >>> 
    >>> # Exemplo 3: Notificar todos
    >>> notificar_todos_usuarios("Manutenção", "Sistema em manutenção hoje às 22h")
    >>> 
    >>> # Exemplo 8: Enviar com verificações
    >>> resultado = enviar_com_verificacao(user, "Teste", "Mensagem de teste")
    >>> print(resultado)
    """
    print("Importe este módulo no Django shell para usar os exemplos")
    print("Ver docstring de __main__ para instruções")

