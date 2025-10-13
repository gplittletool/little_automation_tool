# 📚 Estudo: API do Notion + Estrutura de Base de Dados

**Data:** 13 de Outubro de 2025  
**Objetivo:** Estudar a API do Notion e definir estrutura da base de dados para o sistema de automação de estudos.

---

## 🔵 PARTE 1: API do Notion - Conceitos Fundamentais

### 1.1 O que é a API do Notion?

A API do Notion permite integração programática com workspaces do Notion. Você pode:
- Criar, ler, atualizar e deletar páginas
- Trabalhar com databases
- Adicionar blocos de conteúdo
- Buscar informações

**Documentação oficial:** https://developers.notion.com/

### 1.2 Autenticação

**Existem 2 tipos de integração:**

#### A) Internal Integration (Recomendado para nosso caso)
```
1. Usuário cria uma Integration no Notion (https://www.notion.so/my-integrations)
2. Obtém um "Internal Integration Token"
3. Compartilha o database específico com a integração
4. Cola o token no nosso sistema
```

**Formato do token:**
```
secret_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Vantagens:**
- Simples de implementar
- Usuário tem controle total
- Não requer OAuth complexo

#### B) Public OAuth Integration (Futuro)
- Mais profissional
- Requer OAuth 2.0 flow
- Usuário autoriza pelo próprio Notion

**Para MVP: usar Internal Integration**

---

### 1.3 Estrutura da API

**Base URL:** `https://api.notion.com/v1/`

**Headers necessários:**
```http
Authorization: Bearer secret_XXXXXX
Notion-Version: 2022-06-28
Content-Type: application/json
```

---

### 1.4 Databases no Notion

Um Database é como uma tabela/planilha com propriedades customizáveis.

**Estrutura de um Database:**
```json
{
  "object": "database",
  "id": "abc123...",
  "title": "Plano de Estudos",
  "properties": {
    "Nome": { "type": "title" },
    "Data": { "type": "date" },
    "Matéria": { "type": "select" },
    "Tipo": { "type": "select" },
    "Status": { "type": "select" }
  }
}
```

**Tipos de propriedades relevantes para nós:**
- `title` - Título da página (obrigatório ter 1)
- `rich_text` - Texto formatado
- `select` - Lista de opções única (ex: matéria)
- `multi_select` - Múltiplas opções
- `date` - Data e hora
- `number` - Números
- `checkbox` - Booleano
- `relation` - Relacionamento entre databases

---

### 1.5 Endpoints Principais

#### 🔹 1. Buscar Database
```http
GET /v1/databases/{database_id}
```
**Uso:** Validar se temos acesso e obter estrutura

#### 🔹 2. Criar Página em Database
```http
POST /v1/pages
```
**Body:**
```json
{
  "parent": { "database_id": "abc123..." },
  "properties": {
    "Nome": {
      "title": [{ "text": { "content": "Prova de Cálculo" } }]
    },
    "Data": {
      "date": { "start": "2025-10-20T09:00:00" }
    },
    "Matéria": {
      "select": { "name": "Cálculo I" }
    }
  }
}
```

#### 🔹 3. Atualizar Página
```http
PATCH /v1/pages/{page_id}
```

#### 🔹 4. Buscar Páginas do Database
```http
POST /v1/databases/{database_id}/query
```
**Body (com filtro):**
```json
{
  "filter": {
    "property": "Data",
    "date": {
      "after": "2025-10-13"
    }
  },
  "sorts": [
    {
      "property": "Data",
      "direction": "ascending"
    }
  ]
}
```

---

### 1.6 Estrutura do Database Ideal no Notion

**Para nosso sistema, o usuário deve criar um database com estas propriedades:**

| Propriedade | Tipo | Descrição |
|-------------|------|-----------|
| **Evento** | Title | Nome do evento (Prova, Entrega, etc) |
| **Data** | Date | Data e horário do evento |
| **Matéria** | Select | Nome da disciplina |
| **Tipo** | Select | Prova, Trabalho, Entrega, Revisão, Aula |
| **Descrição** | Rich Text | Detalhes adicionais |
| **Status** | Select | Pendente, Concluído, Cancelado |
| **Origem** | Rich Text | "Gerado automaticamente" |

**Options para "Tipo":**
- 📝 Prova
- 📄 Trabalho
- 📤 Entrega
- 📖 Revisão
- 🎓 Aula
- 📚 Outro

---

### 1.7 Exemplo de Código Python (usando notion-client)

```python
from notion_client import Client

# Inicializar cliente
notion = Client(auth="secret_XXXX")

# Criar página no database
def criar_evento_notion(database_id, evento):
    novo_evento = notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Evento": {
                "title": [
                    {
                        "text": {
                            "content": evento["title"]
                        }
                    }
                ]
            },
            "Data": {
                "date": {
                    "start": evento["date"].isoformat(),
                    "time_zone": "America/Manaus"
                }
            },
            "Matéria": {
                "select": {
                    "name": evento["subject"]
                }
            },
            "Tipo": {
                "select": {
                    "name": evento["event_type"]
                }
            },
            "Descrição": {
                "rich_text": [
                    {
                        "text": {
                            "content": evento["description"]
                        }
                    }
                ]
            }
        }
    )
    return novo_evento["id"]

# Buscar database
def validar_database(database_id):
    try:
        database = notion.databases.retrieve(database_id=database_id)
        return True, database
    except Exception as e:
        return False, str(e)
```

---

## 🗄️ PARTE 2: Estrutura de Base de Dados (PostgreSQL)

### 2.1 Entidades Principais

```
User (Django padrão)
  ↓
UserProfile (1:1)
  ↓
StudyPlan (1:N) ← PDF enviado
  ↓
Subject (N:N) ← Matérias extraídas
  ↓
StudyEvent (1:N) ← Eventos extraídos
  ↓
Notification (1:N) ← Notificações enviadas
```

---

### 2.2 Models Detalhados

#### 🟦 Model 1: UserProfile

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Integração Notion
    notion_token = models.CharField(max_length=255, blank=True, null=True)
    notion_database_id = models.CharField(max_length=50, blank=True, null=True)
    is_notion_connected = models.BooleanField(default=False)
    notion_last_sync = models.DateTimeField(null=True, blank=True)
    
    # Integração Telegram
    telegram_user_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    is_telegram_connected = models.BooleanField(default=False)
    
    # Preferências de notificação
    notify_1_day_before = models.BooleanField(default=True)
    notify_3_hours_before = models.BooleanField(default=True)
    notify_1_hour_before = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile de {self.user.username}"
```

---

#### 🟦 Model 2: Subject (Matéria)

```python
class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)  # Ex: "Cálculo I"
    code = models.CharField(max_length=50, blank=True)  # Ex: "MAT101"
    
    # Controle de frequência
    total_classes = models.IntegerField(default=0)  # Total de aulas no período
    max_absences = models.IntegerField(default=0)  # Limite de faltas permitido
    current_absences = models.IntegerField(default=0)  # Faltas até agora
    
    # Horários regulares
    schedule_info = models.JSONField(default=dict, blank=True)
    # Exemplo de estrutura:
    # {
    #   "Segunda": ["08:00-10:00", "14:00-16:00"],
    #   "Quarta": ["08:00-10:00"]
    # }
    
    # Cores e organização
    color = models.CharField(max_length=7, default="#3B82F6")  # Hex color
    professor = models.CharField(max_length=200, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    semester = models.CharField(max_length=20, blank=True)  # Ex: "2025.1"
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name', 'semester']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def attendance_percentage(self):
        """Calcula percentual de presença"""
        if self.total_classes == 0:
            return 100
        return ((self.total_classes - self.current_absences) / self.total_classes) * 100
    
    @property
    def absences_remaining(self):
        """Faltas restantes antes do limite"""
        return max(0, self.max_absences - self.current_absences)
    
    @property
    def is_at_risk(self):
        """Alerta se está próximo do limite de faltas"""
        return self.current_absences >= (self.max_absences * 0.75)
```

---

#### 🟦 Model 3: StudyPlan

```python
class StudyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Arquivo PDF
    pdf_file = models.FileField(upload_to='study_plans/%Y/%m/')
    file_size = models.IntegerField(default=0)  # em bytes
    
    # Processamento
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendente'),
            ('processing', 'Processando'),
            ('completed', 'Concluído'),
            ('failed', 'Falhou'),
        ],
        default='pending'
    )
    
    # Resultado da IA
    ai_raw_response = models.TextField(blank=True)  # JSON bruto da IA
    ai_analysis = models.JSONField(default=dict, blank=True)
    # Estrutura:
    # {
    #   "period": "2025.1",
    #   "subjects": [...],
    #   "events": [...],
    #   "metadata": {...}
    # }
    
    # Sincronização
    last_synced_to_notion = models.DateTimeField(null=True, blank=True)
    sync_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
```

---

#### 🟦 Model 4: StudyEvent

```python
class StudyEvent(models.Model):
    EVENT_TYPES = [
        ('prova', '📝 Prova'),
        ('trabalho', '📄 Trabalho'),
        ('entrega', '📤 Entrega'),
        ('revisao', '📖 Revisão'),
        ('aula', '🎓 Aula'),
        ('outro', '📚 Outro'),
    ]
    
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='events')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, related_name='events')
    
    # Detalhes do evento
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    
    # Data e hora
    event_date = models.DateField()
    event_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Localização (opcional)
    location = models.CharField(max_length=255, blank=True)
    
    # Sincronização com Notion
    notion_page_id = models.CharField(max_length=50, blank=True, null=True)
    is_synced_to_notion = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    
    # Controle de faltas (se for aula)
    is_absence = models.BooleanField(default=False)
    absence_justified = models.BooleanField(default=False)
    absence_justification = models.TextField(blank=True)
    
    # Metadados
    priority = models.IntegerField(default=0)  # 0-5, maior = mais importante
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['event_date', 'event_time']
        indexes = [
            models.Index(fields=['event_date', 'is_completed']),
            models.Index(fields=['subject', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.event_date}"
    
    @property
    def datetime(self):
        """Retorna datetime completo se tiver horário"""
        if self.event_time:
            from datetime import datetime, time
            return datetime.combine(self.event_date, self.event_time)
        return None
    
    @property
    def is_past(self):
        """Verifica se o evento já passou"""
        from django.utils import timezone
        if self.datetime:
            return self.datetime < timezone.now()
        return self.event_date < timezone.now().date()
    
    @property
    def days_until(self):
        """Dias até o evento"""
        from django.utils import timezone
        today = timezone.now().date()
        return (self.event_date - today).days
```

---

#### 🟦 Model 5: Notification

```python
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('telegram', 'Telegram'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('sent', 'Enviada'),
        ('failed', 'Falhou'),
        ('cancelled', 'Cancelada'),
    ]
    
    study_event = models.ForeignKey(StudyEvent, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Tipo e status
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Conteúdo
    message_title = models.CharField(max_length=255)
    message_text = models.TextField()
    
    # Agendamento
    scheduled_for = models.DateTimeField()  # Quando deve ser enviada
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Erros
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} para {self.user.username} - {self.status}"
```

---

#### 🟦 Model 6: AttendanceRecord (Registro de Frequência)

```python
class AttendanceRecord(models.Model):
    """Registro individual de presença/falta"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendance_records')
    study_event = models.OneToOneField(StudyEvent, on_delete=models.CASCADE, null=True, blank=True)
    
    date = models.DateField()
    was_present = models.BooleanField(default=True)
    is_justified = models.BooleanField(default=False)
    justification = models.TextField(blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['subject', 'date']
        ordering = ['-date']
    
    def __str__(self):
        status = "Presente" if self.was_present else "Falta"
        return f"{self.subject.name} - {self.date} - {status}"
    
    def save(self, *args, **kwargs):
        """Atualiza contador de faltas na matéria"""
        is_new = self.pk is None
        old_was_present = None
        
        if not is_new:
            old_record = AttendanceRecord.objects.get(pk=self.pk)
            old_was_present = old_record.was_present
        
        super().save(*args, **kwargs)
        
        # Atualizar contador de faltas
        if is_new and not self.was_present:
            self.subject.current_absences += 1
            self.subject.save()
        elif not is_new and old_was_present != self.was_present:
            if self.was_present:
                self.subject.current_absences -= 1
            else:
                self.subject.current_absences += 1
            self.subject.save()
```

---

### 2.3 Diagrama de Relacionamentos

```
User (Django Auth)
  |
  └─── UserProfile (1:1)
         ├─── notion_token
         ├─── telegram_chat_id
         └─── preferences
  |
  ├─── Subject (1:N)
  |      ├─── schedule_info
  |      ├─── max_absences
  |      └─── current_absences
  |             |
  |             └─── AttendanceRecord (1:N)
  |
  └─── StudyPlan (1:N)
         ├─── pdf_file
         ├─── ai_analysis
         |
         └─── StudyEvent (1:N)
                ├─── subject (FK)
                ├─── notion_page_id
                |
                └─── Notification (1:N)
```

---

## 🔄 PARTE 3: Fluxo de Dados (Integração)

### 3.1 Fluxo de Upload e Processamento

```
1. Usuário faz upload de PDF
   ↓
2. Criar StudyPlan (status: pending)
   ↓
3. Task Celery: process_pdf_async
   ↓
4. Extrair texto do PDF (PyPDF2)
   ↓
5. Enviar para IA (OpenAI GPT-4)
   ↓
6. IA retorna JSON com:
   - Matérias (subjects)
   - Eventos (events)
   - Horários regulares (schedules)
   - Limites de falta (attendance_limits)
   ↓
7. Criar/atualizar Subject models
   ↓
8. Criar StudyEvent models
   ↓
9. Atualizar StudyPlan (status: completed)
   ↓
10. Disparar sync com Notion (se conectado)
```

### 3.2 Prompt Detalhado para IA

```python
PROMPT_TEMPLATE = """
Você é um assistente especializado em análise de planos de estudo acadêmicos.

Analise o texto abaixo, que foi extraído de um PDF de plano de estudos, e extraia:

1. MATÉRIAS/DISCIPLINAS:
   - Nome completo da disciplina
   - Código (se houver)
   - Professor (se mencionado)
   - Carga horária total (se houver)
   - Limite de faltas permitido (geralmente 25% da carga horária)
   - Horários regulares das aulas (dia da semana + horário)

2. EVENTOS IMPORTANTES:
   - Provas
   - Trabalhos
   - Entregas de projetos
   - Apresentações
   - Revisões
   - Qualquer outro evento com data

Para cada evento, extraia:
   - Data (formato YYYY-MM-DD)
   - Horário (formato HH:MM, se disponível)
   - Nome/título do evento
   - Tipo (prova, trabalho, entrega, etc)
   - Disciplina relacionada
   - Descrição ou detalhes relevantes

IMPORTANTE:
- Se o ano não for mencionado explicitamente, considere 2025
- Converta meses por extenso para números
- Normalize formatos de data variados
- Se houver dúvidas, use "outro" como tipo de evento

Retorne em formato JSON seguindo esta estrutura exata:

{
  "period": "2025.1",
  "subjects": [
    {
      "name": "Nome da Disciplina",
      "code": "ABC123",
      "professor": "Nome do Professor",
      "total_hours": 60,
      "max_absences": 15,
      "schedule": {
        "Segunda": ["08:00-10:00"],
        "Quarta": ["08:00-10:00", "14:00-16:00"]
      }
    }
  ],
  "events": [
    {
      "date": "2025-10-20",
      "time": "09:00",
      "title": "Prova de Cálculo I",
      "description": "Conteúdo: Derivadas e Integrais",
      "event_type": "prova",
      "subject": "Cálculo I",
      "location": "Sala 203"
    }
  ]
}

TEXTO DO PDF:
---
{pdf_text}
---
"""
```

### 3.3 Fluxo de Sincronização com Notion

```python
def sync_events_to_notion(user_profile, study_plan):
    """
    Sincroniza eventos do StudyPlan para o Notion
    """
    notion = Client(auth=user_profile.notion_token)
    database_id = user_profile.notion_database_id
    
    events = study_plan.events.filter(is_synced_to_notion=False)
    
    for event in events:
        try:
            # Criar página no Notion
            page_id = create_notion_page(
                notion=notion,
                database_id=database_id,
                event=event
            )
            
            # Atualizar evento
            event.notion_page_id = page_id
            event.is_synced_to_notion = True
            event.synced_at = timezone.now()
            event.save()
            
        except Exception as e:
            # Log do erro
            print(f"Erro ao sincronizar evento {event.id}: {e}")
            continue
    
    # Atualizar timestamp do plano
    study_plan.last_synced_to_notion = timezone.now()
    study_plan.sync_count += 1
    study_plan.save()

def create_notion_page(notion, database_id, event):
    """Cria uma página no database do Notion"""
    properties = {
        "Evento": {
            "title": [{"text": {"content": event.title}}]
        },
        "Matéria": {
            "select": {"name": event.subject.name if event.subject else "Geral"}
        },
        "Tipo": {
            "select": {"name": event.get_event_type_display()}
        },
        "Status": {
            "select": {"name": "Pendente"}
        }
    }
    
    # Data com horário
    date_value = {"start": event.event_date.isoformat()}
    if event.event_time:
        date_value["start"] = f"{event.event_date}T{event.event_time}"
    if event.end_time:
        date_value["end"] = f"{event.event_date}T{event.end_time}"
    
    properties["Data"] = {"date": date_value}
    
    # Descrição
    if event.description:
        properties["Descrição"] = {
            "rich_text": [{"text": {"content": event.description[:2000]}}]
        }
    
    response = notion.pages.create(
        parent={"database_id": database_id},
        properties=properties
    )
    
    return response["id"]
```

---

## 📊 PARTE 4: Casos de Uso Específicos

### Caso 1: Controle de Faltas

**Objetivo:** Alertar quando usuário está próximo do limite

```python
def check_attendance_alerts(user):
    """Verifica matérias em risco de reprovação por falta"""
    subjects_at_risk = []
    
    for subject in user.subject_set.filter(is_active=True):
        if subject.is_at_risk:
            subjects_at_risk.append({
                'subject': subject,
                'absences_remaining': subject.absences_remaining,
                'percentage': subject.attendance_percentage
            })
    
    return subjects_at_risk
```

**Notificação Telegram:**
```
⚠️ ALERTA DE FREQUÊNCIA

Matéria: Cálculo I
Faltas: 11 de 15 permitidas
Restam apenas: 4 faltas
Percentual de presença: 73.3%

⚡ Atenção! Você está próximo do limite!
```

### Caso 2: Horários Regulares de Aula

**Objetivo:** Criar eventos recorrentes baseados na grade

```python
def generate_class_events(subject, start_date, end_date):
    """Gera eventos de aula baseado na grade horária"""
    from datetime import timedelta
    
    weekday_map = {
        'Segunda': 0,
        'Terça': 1,
        'Quarta': 2,
        'Quinta': 3,
        'Sexta': 4,
        'Sábado': 5
    }
    
    events = []
    current_date = start_date
    
    while current_date <= end_date:
        weekday_name = None
        for name, num in weekday_map.items():
            if current_date.weekday() == num:
                weekday_name = name
                break
        
        if weekday_name and weekday_name in subject.schedule_info:
            for time_range in subject.schedule_info[weekday_name]:
                start_time, end_time = time_range.split('-')
                
                event = StudyEvent.objects.create(
                    subject=subject,
                    title=f"Aula de {subject.name}",
                    event_type='aula',
                    event_date=current_date,
                    event_time=start_time,
                    end_time=end_time
                )
                events.append(event)
        
        current_date += timedelta(days=1)
    
    return events
```

### Caso 3: Dashboard de Visão Geral

**Query para dashboard:**

```python
def get_dashboard_data(user):
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Count, Q
    
    today = timezone.now().date()
    next_week = today + timedelta(days=7)
    
    data = {
        # Próximos eventos
        'upcoming_events': StudyEvent.objects.filter(
            study_plan__user=user,
            event_date__gte=today,
            event_date__lte=next_week,
            is_completed=False
        ).select_related('subject').order_by('event_date', 'event_time')[:5],
        
        # Estatísticas
        'total_events': StudyEvent.objects.filter(
            study_plan__user=user,
            event_date__gte=today
        ).count(),
        
        'total_subjects': Subject.objects.filter(
            user=user,
            is_active=True
        ).count(),
        
        # Matérias em risco
        'subjects_at_risk': Subject.objects.filter(
            user=user,
            is_active=True,
            current_absences__gte=F('max_absences') * 0.75
        ),
        
        # Eventos por tipo (próximos 30 dias)
        'events_by_type': StudyEvent.objects.filter(
            study_plan__user=user,
            event_date__gte=today,
            event_date__lte=today + timedelta(days=30)
        ).values('event_type').annotate(count=Count('id')),
        
        # Status de integrações
        'integrations': {
            'notion': user.userprofile.is_notion_connected,
            'telegram': user.userprofile.is_telegram_connected,
        }
    }
    
    return data
```