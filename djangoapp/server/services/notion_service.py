"""
Serviço de integração com Notion
"""
import logging
from typing import Optional, Dict, Any
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionService:
    """Serviço para sincronização com Notion"""
    
    def __init__(self, token: str, database_id: str):
        """
        Inicializa serviço Notion
        
        Args:
            token: Integration token do Notion
            database_id: ID do database onde serão criadas as páginas
        """
        self.client = Client(auth=token)
        self.database_id = database_id
    
    def validate_connection(self) -> tuple[bool, str]:
        """
        Valida se tem acesso ao database
        
        Returns:
            Tuple (is_valid, message)
        """
        try:
            # Tentar buscar o database
            database = self.client.databases.retrieve(database_id=self.database_id)
            
            # Verificar se tem as propriedades básicas necessárias
            properties = database.get('properties', {})
            
            # O database deve ter pelo menos um campo "title"
            has_title = any(
                prop.get('type') == 'title' 
                for prop in properties.values()
            )
            
            if not has_title:
                return False, "Database não tem campo de título"
            
            return True, "Conexão válida"
            
        except APIResponseError as e:
            logger.error(f"Erro ao validar conexão Notion: {e}")
            return False, f"Erro de API: {e.message}"
        except Exception as e:
            logger.error(f"Erro ao validar Notion: {e}")
            return False, str(e)
    
    def create_event_page(self, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Cria página no Notion para um evento
        
        Args:
            event_data: Dict com dados do evento
                {
                    'title': str,
                    'date': str (YYYY-MM-DD),
                    'time': str (HH:MM) optional,
                    'type': str,
                    'subject': str optional,
                    'description': str optional,
                    'location': str optional
                }
        
        Returns:
            ID da página criada ou None se erro
        """
        try:
            # Preparar propriedades
            properties = {}
            
            # Título (obrigatório - buscar campo title)
            properties["Evento"] = {
                "title": [
                    {
                        "text": {
                            "content": event_data.get('title', 'Sem título')
                        }
                    }
                ]
            }
            
            # Data
            date_value = {"start": event_data['date']}
            if event_data.get('time'):
                date_value['start'] = f"{event_data['date']}T{event_data['time']}:00"
            
            properties["Data"] = {
                "date": date_value
            }
            
            # Tipo
            if event_data.get('type'):
                properties["Tipo"] = {
                    "select": {
                        "name": self._format_event_type(event_data['type'])
                    }
                }
            
            # Matéria
            if event_data.get('subject'):
                properties["Matéria"] = {
                    "select": {
                        "name": event_data['subject']
                    }
                }
            
            # Descrição
            if event_data.get('description'):
                properties["Descrição"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": event_data['description'][:2000]  # Limite do Notion
                            }
                        }
                    ]
                }
            
            # Local
            if event_data.get('location'):
                properties["Local"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": event_data['location']
                            }
                        }
                    ]
                }
            
            # Status padrão
            properties["Status"] = {
                "select": {
                    "name": "Pendente"
                }
            }
            
            # Criar página
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = page['id']
            logger.info(f"Página Notion criada: {page_id}")
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Erro ao criar página no Notion: {e}")
            logger.error(f"Status: {e.status}, Message: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao criar página: {e}")
            return None
    
    def update_event_page(self, page_id: str, event_data: Dict[str, Any]) -> bool:
        """
        Atualiza página existente no Notion
        
        Args:
            page_id: ID da página
            event_data: Novos dados
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            properties = {}
            
            if event_data.get('title'):
                properties["Evento"] = {
                    "title": [{"text": {"content": event_data['title']}}]
                }
            
            if event_data.get('date'):
                date_value = {"start": event_data['date']}
                if event_data.get('time'):
                    date_value['start'] = f"{event_data['date']}T{event_data['time']}:00"
                properties["Data"] = {"date": date_value}
            
            if properties:
                self.client.pages.update(
                    page_id=page_id,
                    properties=properties
                )
                logger.info(f"Página Notion atualizada: {page_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao atualizar página: {e}")
            return False
    
    @staticmethod
    def _format_event_type(event_type: str) -> str:
        """Formata tipo de evento para o Notion"""
        type_map = {
            'prova': '📝 Prova',
            'trabalho': '📄 Trabalho',
            'entrega': '📤 Entrega',
            'revisao': '📖 Revisão',
            'aula': '🎓 Aula',
            'outro': '📚 Outro'
        }
        return type_map.get(event_type, event_type)

