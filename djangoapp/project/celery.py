"""
Configuração do Celery
"""
import os
from celery import Celery

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

# Load config from Django settings (prefixed with CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

