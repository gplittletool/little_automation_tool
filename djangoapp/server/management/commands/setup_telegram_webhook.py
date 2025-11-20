"""
Comando para configurar o webhook do Telegram
"""
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Configura o webhook do Telegram Bot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove o webhook ao invés de configurar',
        )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        
        if not token:
            self.stdout.write(
                self.style.ERROR('TELEGRAM_BOT_TOKEN não configurado!')
            )
            return

        if options['remove']:
            # Remover webhook
            url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            response = requests.post(url)
            
            if response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS('✅ Webhook removido com sucesso!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro ao remover webhook: {response.text}')
                )
        else:
            # Configurar webhook
            webhook_url = settings.TELEGRAM_WEBHOOK_URL
            
            if not webhook_url:
                self.stdout.write(
                    self.style.WARNING(
                        'TELEGRAM_WEBHOOK_URL não configurado. '
                        'Bot funcionará em modo polling (para desenvolvimento local).'
                    )
                )
                return
            
            url = f"https://api.telegram.org/bot{token}/setWebhook"
            data = {'url': webhook_url}
            
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Webhook configurado: {webhook_url}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro ao configurar webhook: {response.text}')
                )
        
        # Mostrar informações do webhook
        info_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        response = requests.get(info_url)
        
        if response.status_code == 200:
            info = response.json()
            self.stdout.write('\n' + '='*50)
            self.stdout.write('📊 Informações do Webhook:')
            self.stdout.write('='*50)
            
            webhook_info = info.get('result', {})
            self.stdout.write(f"URL: {webhook_info.get('url', 'Nenhum')}")
            self.stdout.write(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
            
            if webhook_info.get('last_error_message'):
                self.stdout.write(
                    self.style.WARNING(f"Último erro: {webhook_info['last_error_message']}")
                )

