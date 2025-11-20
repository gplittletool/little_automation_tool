"""
Serializers DRF para API
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Subject, StudyPlan, StudyEvent


class UserSerializer(serializers.ModelSerializer):
    """Serializer para User"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer para UserProfile"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user',
            'is_telegram_connected', 'telegram_username',
            'is_notion_connected',
            'notifications_enabled',
            'created_at'
        ]
        read_only_fields = ['is_telegram_connected', 'is_notion_connected']


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer para Subject"""
    attendance_percentage = serializers.ReadOnlyField()
    absences_remaining = serializers.ReadOnlyField()
    is_at_risk = serializers.ReadOnlyField()
    
    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'professor', 'semester',
            'total_classes', 'max_absences', 'current_absences',
            'attendance_percentage', 'absences_remaining', 'is_at_risk',
            'color', 'is_active', 'schedule_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StudyEventSerializer(serializers.ModelSerializer):
    """Serializer para StudyEvent"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    study_plan_title = serializers.CharField(source='study_plan.title', read_only=True)
    days_until = serializers.ReadOnlyField()
    is_past = serializers.ReadOnlyField()
    
    class Meta:
        model = StudyEvent
        fields = [
            'id', 'title', 'description', 'event_type',
            'event_date', 'event_time', 'end_time', 'location',
            'priority', 'is_completed', 'completed_at',
            'subject', 'subject_name',
            'study_plan', 'study_plan_title',
            'days_until', 'is_past',
            'synced_to_notion',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'study_plan']


class StudyPlanListSerializer(serializers.ModelSerializer):
    """Serializer para lista de StudyPlans"""
    events_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudyPlan
        fields = [
            'id', 'title', 'description', 'status',
            'events_created', 'subjects_created', 'events_count',
            'synced_to_notion',
            'created_at', 'processed_at'
        ]
        read_only_fields = ['status', 'events_created', 'subjects_created', 'synced_to_notion']
    
    def get_events_count(self, obj):
        return obj.events.count()


class StudyPlanDetailSerializer(serializers.ModelSerializer):
    """Serializer detalhado para StudyPlan"""
    events = StudyEventSerializer(many=True, read_only=True)
    
    class Meta:
        model = StudyPlan
        fields = [
            'id', 'title', 'description', 'status',
            'pdf_file', 'file_size',
            'events_created', 'subjects_created',
            'ai_analysis', 'error_message',
            'synced_to_notion', 'synced_at',
            'created_at', 'processed_at', 'updated_at',
            'events'
        ]
        read_only_fields = [
            'status', 'file_size', 'events_created', 'subjects_created',
            'ai_analysis', 'synced_to_notion', 'synced_at',
            'created_at', 'processed_at', 'updated_at'
        ]


class StudyPlanUploadSerializer(serializers.ModelSerializer):
    """Serializer para upload de PDF"""
    
    class Meta:
        model = StudyPlan
        fields = ['title', 'description', 'pdf_file']
    
    def validate_pdf_file(self, value):
        """Valida arquivo PDF"""
        # Validar extensão
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Apenas arquivos PDF são permitidos")
        
        # Validar tamanho (máximo 10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Arquivo muito grande. Máximo: 10MB")
        
        return value
    
    def create(self, validated_data):
        """Cria StudyPlan e salva tamanho do arquivo"""
        pdf_file = validated_data.get('pdf_file')
        validated_data['file_size'] = pdf_file.size if pdf_file else 0
        
        # User será adicionado na view
        return super().create(validated_data)

