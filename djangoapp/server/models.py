from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
import string


class UserProfile(models.Model):
    """Perfil estendido do usuário com informações de integração"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Integração Telegram
    telegram_user_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    telegram_first_name = models.CharField(max_length=100, blank=True, null=True)
    telegram_last_name = models.CharField(max_length=100, blank=True, null=True)
    is_telegram_connected = models.BooleanField(default=False)
    telegram_connected_at = models.DateTimeField(null=True, blank=True)
    
    # Integração Notion
    notion_token = models.CharField(max_length=255, blank=True, null=True, verbose_name='Notion Token')
    notion_database_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='Notion Database ID')
    is_notion_connected = models.BooleanField(default=False, verbose_name='Notion Conectado')
    notion_connected_at = models.DateTimeField(null=True, blank=True)
    
    # Preferências de notificação
    notifications_enabled = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'
    
    def __str__(self):
        return f"Profile de {self.user.username}"
    
    def disconnect_telegram(self):
        """Desconecta a conta do Telegram"""
        self.telegram_user_id = None
        self.telegram_chat_id = None
        self.telegram_username = None
        self.telegram_first_name = None
        self.telegram_last_name = None
        self.is_telegram_connected = False
        self.telegram_connected_at = None
        self.save()
    
    def disconnect_notion(self):
        """Desconecta a conta do Notion"""
        self.notion_token = None
        self.notion_database_id = None
        self.is_notion_connected = False
        self.notion_connected_at = None
        self.save()


class TelegramVerificationCode(models.Model):
    """Código de verificação para conectar conta do Telegram"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_codes')
    code = models.CharField(max_length=8, unique=True)
    
    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Expiração
    expires_at = models.DateTimeField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Código de Verificação Telegram'
        verbose_name_plural = 'Códigos de Verificação Telegram'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'is_used']),
            models.Index(fields=['user', 'is_used']),
        ]
    
    def __str__(self):
        return f"Código {self.code} - {self.user.username}"
    
    @classmethod
    def generate_code(cls, user, validity_hours=24):
        """Gera um código único de 8 caracteres"""
        # Desativar códigos antigos do usuário
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Gerar código único
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not cls.objects.filter(code=code).exists():
                break
        
        # Criar novo código
        expires_at = timezone.now() + timezone.timedelta(hours=validity_hours)
        return cls.objects.create(user=user, code=code, expires_at=expires_at)
    
    def is_valid(self):
        """Verifica se o código ainda é válido"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def mark_as_used(self):
        """Marca o código como usado"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()


class TelegramNotification(models.Model):
    """Registro de notificações enviadas via Telegram"""
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('sent', 'Enviada'),
        ('failed', 'Falhou'),
        ('cancelled', 'Cancelada'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_notifications')
    
    # Conteúdo
    message_title = models.CharField(max_length=255, blank=True)
    message_text = models.TextField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Envio
    sent_at = models.DateTimeField(null=True, blank=True)
    telegram_message_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Erros
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notificação Telegram'
        verbose_name_plural = 'Notificações Telegram'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.status} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class Subject(models.Model):
    """Matéria/Disciplina do plano de estudos"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=200, verbose_name='Nome da Matéria')
    code = models.CharField(max_length=50, blank=True, verbose_name='Código')
    professor = models.CharField(max_length=200, blank=True, verbose_name='Professor')
    
    # Controle de frequência
    total_classes = models.IntegerField(default=0, verbose_name='Total de Aulas')
    max_absences = models.IntegerField(default=0, verbose_name='Limite de Faltas')
    current_absences = models.IntegerField(default=0, verbose_name='Faltas Atuais')
    
    # Horários (JSON: {"Segunda": ["08:00-10:00"], "Quarta": ["14:00-16:00"]})
    schedule_info = models.JSONField(default=dict, blank=True, verbose_name='Horários')
    
    # Organização
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name='Cor')
    semester = models.CharField(max_length=20, blank=True, verbose_name='Semestre')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    
    # Notion sync
    notion_page_id = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Matéria'
        verbose_name_plural = 'Matérias'
        unique_together = ['user', 'name', 'semester']
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.semester})" if self.semester else self.name
    
    @property
    def attendance_percentage(self):
        """Percentual de presença"""
        if self.total_classes == 0:
            return 100
        return ((self.total_classes - self.current_absences) / self.total_classes) * 100
    
    @property
    def absences_remaining(self):
        """Faltas restantes"""
        return max(0, self.max_absences - self.current_absences)
    
    @property
    def is_at_risk(self):
        """Alerta se próximo do limite"""
        if self.max_absences == 0:
            return False
        return self.current_absences >= (self.max_absences * 0.75)


class StudyPlan(models.Model):
    """Plano de estudos (PDF enviado pelo usuário)"""
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    title = models.CharField(max_length=255, verbose_name='Título')
    description = models.TextField(blank=True, verbose_name='Descrição')
    
    # Arquivo
    pdf_file = models.FileField(upload_to='study_plans/%Y/%m/', verbose_name='Arquivo PDF')
    file_size = models.IntegerField(default=0, verbose_name='Tamanho (bytes)')
    
    # Processamento
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Resultado da IA
    ai_raw_response = models.TextField(blank=True, verbose_name='Resposta Bruta da IA')
    ai_analysis = models.JSONField(default=dict, blank=True, verbose_name='Análise Estruturada')
    
    # Estatísticas
    events_created = models.IntegerField(default=0, verbose_name='Eventos Criados')
    subjects_created = models.IntegerField(default=0, verbose_name='Matérias Criadas')
    
    # Sincronização
    synced_to_notion = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    
    # Erros
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plano de Estudos'
        verbose_name_plural = 'Planos de Estudos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class StudyEvent(models.Model):
    """Evento de estudo extraído do PDF"""
    EVENT_TYPES = [
        ('prova', '📝 Prova'),
        ('trabalho', '📄 Trabalho'),
        ('entrega', '📤 Entrega'),
        ('revisao', '📖 Revisão'),
        ('aula', '🎓 Aula'),
        ('outro', '📚 Outro'),
    ]
    
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='events')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    
    # Detalhes
    title = models.CharField(max_length=255, verbose_name='Título')
    description = models.TextField(blank=True, verbose_name='Descrição')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, verbose_name='Tipo')
    
    # Data e hora
    event_date = models.DateField(verbose_name='Data')
    event_time = models.TimeField(null=True, blank=True, verbose_name='Horário')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Horário Fim')
    
    # Local
    location = models.CharField(max_length=255, blank=True, verbose_name='Local')
    
    # Notion sync
    notion_page_id = models.CharField(max_length=50, blank=True, null=True)
    synced_to_notion = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    priority = models.IntegerField(default=3, verbose_name='Prioridade')  # 1-5
    is_completed = models.BooleanField(default=False, verbose_name='Concluído')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Notificações enviadas
    notification_sent_1d = models.BooleanField(default=False, verbose_name='Notif. 1 dia antes')
    notification_sent_3h = models.BooleanField(default=False, verbose_name='Notif. 3h antes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Evento de Estudo'
        verbose_name_plural = 'Eventos de Estudo'
        ordering = ['event_date', 'event_time']
        indexes = [
            models.Index(fields=['event_date', 'is_completed']),
            models.Index(fields=['study_plan', 'event_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.event_date}"
    
    @property
    def datetime_combined(self):
        """Retorna datetime completo"""
        if self.event_time:
            from datetime import datetime
            return datetime.combine(self.event_date, self.event_time)
        return None
    
    @property
    def is_past(self):
        """Verifica se já passou"""
        today = timezone.now().date()
        return self.event_date < today
    
    @property
    def days_until(self):
        """Dias até o evento"""
        today = timezone.now().date()
        delta = self.event_date - today
        return delta.days
