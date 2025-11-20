# 🎓 Little Automation Tool

Sistema inteligente de automação de estudos com IA, que analisa PDFs, extrai eventos automaticamente e sincroniza com Notion + Telegram.

## Features

- **Upload de PDF** - Envie seu plano de estudos
- **IA Analisa** - GPT-4 ou LM Studio extraem eventos e matérias
- **Criação Automática** - Matérias e eventos no sistema
- **Sincroniza Notion** - Eventos aparecem automaticamente
- **Notifica Telegram** - Lembretes antes dos eventos
- **Controle de Faltas** - Acompanhe sua frequência
- **Lembretes Automáticos** - 1 dia e 3 horas antes

**Resultado:** De 3 horas digitando → 1 minuto automático!

---

## Tech Stack

- **Backend:** Django 4.2 + Django REST Framework
- **Database:** PostgreSQL
- **Cache/Queue:** Redis + Celery
- **IA:** OpenAI GPT-4 ou LM Studio (local)
- **Integrações:** Telegram Bot API + Notion API
- **Deploy:** Railway (recomendado) ou Docker

---

## Deploy no Railway (Recomendado)

### Quick Start

1. **Fork este repositório**

2. **Criar projeto no Railway:**
   - Conectar com GitHub
   - Adicionar PostgreSQL
   - Adicionar Redis

3. **Configurar variáveis de ambiente:**
   ```env
   SECRET_KEY=sua-secret-key
   DEBUG=False
   TELEGRAM_BOT_TOKEN=seu-token
   TELEGRAM_WEBHOOK_URL=https://seu-app.railway.app/webhook/telegram/
   OPENAI_API_KEY=sk-... (opcional)
   ```

4. **Deploy automático!** 

** Guia completo:** [`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md)

---

## Desenvolvimento Local (Docker)

### Pré-requisitos

- Docker & Docker Compose
- Bot do Telegram (@BotFather)
- ngrok (para webhook local)

### Setup

```bash
# 1. Clonar repositório
git clone https://github.com/seu-usuario/little-automation-tool.git
cd little-automation-tool

# 2. Configurar .env
cp dotenv_files/.env.example dotenv_files/.env
# Editar .env com suas credenciais

# 3. Iniciar containers
docker-compose up --build -d

# 4. Executar migrations
docker-compose exec djangoapp python manage.py migrate

# 5. Criar superuser
docker-compose exec djangoapp python manage.py createsuperuser

# 6. Acessar
http://localhost:8000/
```

---

## Configurar Telegram

### 1. Criar Bot

1. Abrir @BotFather no Telegram
2. `/newbot`
3. Copiar token

### 2. Configurar Webhook

**Produção (Railway):**
```bash
# Automático via management command
python manage.py setup_telegram_webhook
```

**Local (ngrok):**
```bash
# Terminal 1: Iniciar ngrok
ngrok http 8000

# Terminal 2: Configurar
docker-compose exec djangoapp python manage.py setup_telegram_webhook
```

### 3. Conectar Conta

1. Acessar `/telegram/integration/`
2. Gerar código
3. Clicar no Deep Link ou enviar `/start CODIGO` no bot

---

## IA: OpenAI ou LM Studio

### Opção 1: OpenAI (Nuvem)

```env
OPENAI_API_KEY=sk-proj-...
```

**Custo:** ~$0.03-0.10 por PDF

### Opção 2: LM Studio (Local, Grátis)

1. Baixar LM Studio: https://lmstudio.ai/
2. Baixar modelo: `llama-3.1-8b-instruct`
3. Iniciar servidor local

```env
OPENAI_BASE_URL=http://host.docker.internal:1234/v1
OPENAI_MODEL=llama-3.1-8b-instruct
```

**Custo:** Grátis!

---

## Estrutura do Projeto

```
little_automation_tool/
├── djangoapp/
│   ├── project/              # Settings
│   ├── server/               # App principal
│   │   ├── models.py        # Models (User, Subject, Event, etc)
│   │   ├── views.py         # Views HTML
│   │   ├── views_study.py   # Views de estudo
│   │   ├── serializers.py   # DRF serializers
│   │   ├── tasks.py         # Celery tasks
│   │   ├── services/        # Serviços
│   │   │   ├── pdf_processor.py
│   │   │   ├── ai_service.py
│   │   │   ├── notion_service.py
│   │   │   └── telegram_service.py
│   │   └── templates/       # HTML templates
│   └── requirements.txt
├── docker-compose.yml        # Docker local
├── Dockerfile.railway        # Railway deploy
├── railway.json             # Railway config
└── Procfile                 # Railway services

```

---

## Fluxo do Sistema

```
1. Usuário faz upload de PDF
   ↓
2. PDFProcessor extrai texto
   ↓
3. AIService (GPT-4/LM Studio) analisa
   ↓
4. Cria Matérias + Eventos no banco
   ↓
5. NotionService sincroniza
   ↓
6. TelegramService notifica
   ↓
7. Celery Beat envia lembretes automáticos
```

---

## Roadmap

- [x] Sistema de autenticação
- [x] Upload e processamento de PDF
- [x] Análise com IA (GPT-4/LM Studio)
- [x] Integração Telegram
- [x] Integração Notion
- [x] Notificações automáticas
- [x] Controle de faltas
- [ ] App mobile (React Native)
- [ ] Calendário visual (FullCalendar.js)
- [ ] Exportação iCal/Google Calendar
- [ ] Gamificação
- [ ] Notas de provas
