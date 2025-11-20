from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, TelegramVerificationCode, TelegramNotification,
    Subject, StudyPlan, StudyEvent
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_username', 'is_telegram_connected', 'notifications_enabled', 'created_at']
    list_filter = ['is_telegram_connected', 'notifications_enabled', 'created_at']
    search_fields = ['user__username', 'user__email', 'telegram_username']
    readonly_fields = ['created_at', 'updated_at', 'telegram_connected_at']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('user',)
        }),
        ('Integração Telegram', {
            'fields': (
                'telegram_user_id',
                'telegram_chat_id',
                'telegram_username',
                'telegram_first_name',
                'telegram_last_name',
                'is_telegram_connected',
                'telegram_connected_at',
            )
        }),
        ('Preferências', {
            'fields': ('notifications_enabled',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(TelegramVerificationCode)
class TelegramVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'user', 'is_used', 'is_expired', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['code', 'user__username', 'user__email']
    readonly_fields = ['code', 'created_at', 'used_at']
    
    fieldsets = (
        ('Código', {
            'fields': ('code', 'user')
        }),
        ('Status', {
            'fields': ('is_used', 'used_at', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def is_expired(self, obj):
        from django.utils import timezone
        if obj.expires_at < timezone.now():
            return format_html('<span style="color: red;">❌ Expirado</span>')
        return format_html('<span style="color: green;">✅ Válido</span>')
    
    is_expired.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(TelegramNotification)
class TelegramNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'message_title', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'created_at', 'sent_at']
    search_fields = ['user__username', 'message_title', 'message_text']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'telegram_message_id']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('user',)
        }),
        ('Conteúdo', {
            'fields': ('message_title', 'message_text')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'telegram_message_id')
        }),
        ('Erros e Tentativas', {
            'fields': ('error_message', 'retry_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
