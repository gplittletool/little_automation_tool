"""
Serviço de integração com Telegram Bot
"""
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramService:
    """Serviço para gerenciar comunicação com Telegram"""
    
    _bot = None
    _application = None
    
    @classmethod
    def get_bot(cls) -> Bot:
        """Retorna instância singleton do bot"""
        if cls._bot is None:
            token = settings.TELEGRAM_BOT_TOKEN
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN não configurado")
            cls._bot = Bot(token=token)
        return cls._bot
    
    @classmethod
    def get_application(cls) -> Application:
        """Retorna instância singleton da aplicação"""
        if cls._application is None:
            token = settings.TELEGRAM_BOT_TOKEN
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN não configurado")
            cls._application = Application.builder().token(token).build()
        return cls._application
    
    @classmethod
    async def send_message(
        cls,
        chat_id: str,
        text: str,
        parse_mode: str = 'HTML',
        disable_notification: bool = False,
        reply_markup=None
    ) -> Optional[Dict[str, Any]]:
        """
        Envia uma mensagem para um chat do Telegram
        
        Args:
            chat_id: ID do chat
            text: Texto da mensagem
            parse_mode: Modo de parse (HTML ou Markdown)
            disable_notification: Se True, não notifica o usuário
            reply_markup: Markup para botões inline
            
        Returns:
            Dict com informações da mensagem enviada ou None em caso de erro
        """
        try:
            bot = cls.get_bot()
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                reply_markup=reply_markup
            )
            
            logger.info(f"Mensagem enviada com sucesso para chat_id={chat_id}")
            
            return {
                'message_id': message.message_id,
                'chat_id': message.chat_id,
                'date': message.date,
                'text': message.text
            }
            
        except TelegramError as e:
            logger.error(f"Erro ao enviar mensagem para chat_id={chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar mensagem: {e}")
            return None
    
    @classmethod
    async def send_notification(
        cls,
        user_profile,
        title: str,
        message: str,
        notification_model=None
    ) -> bool:
        """
        Envia uma notificação para um usuário
        
        Args:
            user_profile: Instância de UserProfile
            title: Título da notificação
            message: Conteúdo da mensagem
            notification_model: Instância de TelegramNotification (opcional)
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        if not user_profile.is_telegram_connected:
            logger.warning(f"Usuário {user_profile.user.username} não tem Telegram conectado")
            return False
        
        if not user_profile.notifications_enabled:
            logger.info(f"Notificações desabilitadas para {user_profile.user.username}")
            return False
        
        # Formatar mensagem com título
        formatted_message = f"<b>{title}</b>\n\n{message}"
        
        # Enviar mensagem
        result = await cls.send_message(
            chat_id=user_profile.telegram_chat_id,
            text=formatted_message
        )
        
        # Atualizar modelo de notificação se fornecido
        if notification_model:
            if result:
                notification_model.status = 'sent'
                notification_model.sent_at = timezone.now()
                notification_model.telegram_message_id = str(result['message_id'])
            else:
                notification_model.status = 'failed'
                notification_model.error_message = 'Falha ao enviar mensagem via Telegram'
                notification_model.retry_count += 1
            
            notification_model.save()
        
        return result is not None
    
    @classmethod
    async def verify_code(cls, code: str, telegram_user_id: str, chat_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifica código de verificação e conecta conta
        
        Args:
            code: Código de verificação
            telegram_user_id: ID do usuário no Telegram
            chat_id: ID do chat
            user_data: Dados do usuário do Telegram
            
        Returns:
            Dict com resultado da verificação
        """
        from server.models import TelegramVerificationCode, UserProfile
        
        try:
            # Buscar código válido
            verification = TelegramVerificationCode.objects.filter(
                code=code.upper(),
                is_used=False
            ).first()
            
            if not verification:
                return {
                    'success': False,
                    'message': '❌ Código inválido ou já utilizado.'
                }
            
            if not verification.is_valid():
                return {
                    'success': False,
                    'message': '❌ Código expirado. Gere um novo código no sistema.'
                }
            
            # Verificar se já existe outro usuário com este telegram_user_id
            existing_profile = UserProfile.objects.filter(
                telegram_user_id=telegram_user_id
            ).exclude(user=verification.user).first()
            
            if existing_profile:
                # Desconectar do perfil anterior
                existing_profile.disconnect_telegram()
            
            # Obter ou criar perfil
            profile, created = UserProfile.objects.get_or_create(user=verification.user)
            
            # Atualizar informações do Telegram
            profile.telegram_user_id = telegram_user_id
            profile.telegram_chat_id = chat_id
            profile.telegram_username = user_data.get('username', '')
            profile.telegram_first_name = user_data.get('first_name', '')
            profile.telegram_last_name = user_data.get('last_name', '')
            profile.is_telegram_connected = True
            profile.telegram_connected_at = timezone.now()
            profile.save()
            
            # Marcar código como usado
            verification.mark_as_used()
            
            logger.info(f"Conta Telegram conectada com sucesso para usuário {verification.user.username}")
            
            return {
                'success': True,
                'message': f'✅ Conta conectada com sucesso!\n\nOlá, {verification.user.first_name or verification.user.username}! Você agora receberá notificações neste chat.',
                'user': verification.user
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar código: {e}")
            return {
                'success': False,
                'message': '❌ Erro ao processar código. Tente novamente.'
            }
    
    @classmethod
    def format_notification(cls, title: str, message: str, event_data: Optional[Dict] = None) -> str:
        """
        Formata uma notificação com template padrão
        
        Args:
            title: Título da notificação
            message: Mensagem principal
            event_data: Dados adicionais do evento (opcional)
            
        Returns:
            String formatada em HTML
        """
        formatted = f"<b>🔔 {title}</b>\n\n{message}"
        
        if event_data:
            if 'date' in event_data:
                formatted += f"\n\n📅 <b>Data:</b> {event_data['date']}"
            if 'time' in event_data:
                formatted += f"\n⏰ <b>Horário:</b> {event_data['time']}"
            if 'location' in event_data:
                formatted += f"\n📍 <b>Local:</b> {event_data['location']}"
            if 'subject' in event_data:
                formatted += f"\n📚 <b>Matéria:</b> {event_data['subject']}"
        
        return formatted


class TelegramBotHandlers:
    """Handlers para comandos do bot"""
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /start - com suporte a deep link"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Verificar se veio código via deep link (ex: /start ABC12345)
        if context.args and len(context.args) > 0:
            code = context.args[0].upper()
            
            # Dados do usuário
            user_data = {
                'username': user.username or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or ''
            }
            
            # Tentar verificar automaticamente
            result = await TelegramService.verify_code(
                code=code,
                telegram_user_id=str(user.id),
                chat_id=str(chat_id),
                user_data=user_data
            )
            
            await update.message.reply_text(
                result['message'],
                parse_mode='HTML'
            )
            return
        
        # Verificar se usuário já está conectado
        from server.models import UserProfile
        
        try:
            profile = UserProfile.objects.filter(
                telegram_user_id=str(user.id),
                is_telegram_connected=True
            ).first()
            
            if profile:
                # Já conectado
                already_connected_msg = (
                    f"👋 Olá, {user.first_name}!\n\n"
                    f"✅ <b>Você já está conectado!</b>\n\n"
                    f"👤 Conta: <b>{profile.user.username}</b>\n"
                    f"📱 Telegram: @{user.username or user.first_name}\n\n"
                    f"🔔 <b>Você já recebe notificações de:</b>\n"
                    f"• Eventos próximos (1 dia e 3h antes)\n"
                    f"• Processamento de PDFs concluído\n"
                    f"• Alertas de faltas em matérias\n\n"
                    f"💡 Digite /help para ver os comandos disponíveis."
                )
                
                await update.message.reply_text(
                    already_connected_msg,
                    parse_mode='HTML'
                )
                return
        except Exception as e:
            logger.error(f"Erro ao verificar perfil existente: {e}")
        
        # Mensagem de boas-vindas para novo usuário
        welcome_message = (
            f"👋 Olá, <b>{user.first_name}</b>!\n\n"
            f"Bem-vindo ao <b>Sistema de Automação de Estudos</b>! 🎓\n\n"
            f"🤖 <b>Eu posso te ajudar com:</b>\n"
            f"• 📅 Lembretes de provas e trabalhos\n"
            f"• ⏰ Notificações de eventos próximos\n"
            f"• 📊 Alertas de controle de faltas\n"
            f"• ✅ Confirmação de processamento de PDFs\n\n"
            f"🔗 <b>Para conectar sua conta:</b>\n\n"
            f"<b>Via Deep Link (Rápido):</b>\n"
            f"1️⃣ Acesse: <code>http://localhost:8000/telegram/integration/</code>\n"
            f"2️⃣ Clique no botão 'Abrir no Telegram'\n"
            f"3️⃣ Pronto! ✅\n\n"
            f"<b>Via Código Manual:</b>\n"
            f"1️⃣ Acesse o sistema web\n"
            f"2️⃣ Gere um código de 8 dígitos\n"
            f"3️⃣ Envie aqui: <code>/verificar CODIGO</code>\n\n"
            f"📖 Digite /help para ver todos os comandos.\n\n"
            f"💡 <b>Dica:</b> Use o Deep Link, é mais rápido!"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='HTML'
        )
    
    @staticmethod
    async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /verificar"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Verificar se código foi fornecido
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "❌ <b>Código não fornecido</b>\n\n"
                "Use: <code>/verificar SEU_CODIGO</code>\n\n"
                "Exemplo: <code>/verificar ABC12345</code>",
                parse_mode='HTML'
            )
            return
        
        code = context.args[0].upper()
        
        # Dados do usuário
        user_data = {
            'username': user.username or '',
            'first_name': user.first_name or '',
            'last_name': user.last_name or ''
        }
        
        # Verificar código
        result = await TelegramService.verify_code(
            code=code,
            telegram_user_id=str(user.id),
            chat_id=str(chat_id),
            user_data=user_data
        )
        
        await update.message.reply_text(
            result['message'],
            parse_mode='HTML'
        )
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /help"""
        help_message = (
            "<b>📖 Comandos Disponíveis</b>\n\n"
            "/start - Iniciar bot\n"
            "/verificar CODIGO - Conectar sua conta\n"
            "/status - Ver status da conexão\n"
            "/help - Mostrar esta ajuda\n\n"
            "<b>💡 Dicas:</b>\n"
            "• Mantenha as notificações ativadas\n"
            "• Não bloqueie o bot\n"
            "• Configure suas preferências no sistema web"
        )
        
        await update.message.reply_text(
            help_message,
            parse_mode='HTML'
        )
    
    @staticmethod
    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /status"""
        from server.models import UserProfile
        
        user = update.effective_user
        telegram_user_id = str(user.id)
        
        # Buscar perfil conectado
        profile = UserProfile.objects.filter(
            telegram_user_id=telegram_user_id,
            is_telegram_connected=True
        ).first()
        
        if profile:
            status_message = (
                f"✅ <b>Conta Conectada</b>\n\n"
                f"👤 <b>Usuário:</b> {profile.user.username}\n"
                f"📧 <b>Email:</b> {profile.user.email}\n"
                f"🔔 <b>Notificações:</b> {'Ativadas' if profile.notifications_enabled else 'Desativadas'}\n"
                f"📅 <b>Conectado em:</b> {profile.telegram_connected_at.strftime('%d/%m/%Y às %H:%M')}\n\n"
                f"Para gerenciar suas configurações, acesse o sistema web."
            )
        else:
            status_message = (
                "❌ <b>Conta não conectada</b>\n\n"
                "Para conectar:\n"
                "1. Acesse o sistema web\n"
                "2. Gere um código de verificação\n"
                "3. Use <code>/verificar SEU_CODIGO</code>"
            )
        
        await update.message.reply_text(
            status_message,
            parse_mode='HTML'
        )


def setup_bot_handlers(application: Application):
    """Configura os handlers do bot"""
    
    # Comandos
    application.add_handler(CommandHandler("start", TelegramBotHandlers.start_command))
    application.add_handler(CommandHandler("verificar", TelegramBotHandlers.verify_command))
    application.add_handler(CommandHandler("help", TelegramBotHandlers.help_command))
    application.add_handler(CommandHandler("status", TelegramBotHandlers.status_command))
    
    logger.info("Handlers do bot configurados")

