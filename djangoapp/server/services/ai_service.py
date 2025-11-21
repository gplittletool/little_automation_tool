"""
Serviço de IA para análise de planos de estudo
Suporta: Google Gemini, OpenAI API e LM Studio (local)
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from django.conf import settings
import openai

logger = logging.getLogger(__name__)

# Tentar importar Gemini (pode não estar instalado)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai não instalado. Use: pip install google-generativeai")


class AIService:
    """Serviço para análise de PDFs com GPT-4"""
    
    PROMPT_TEMPLATE = """
Você é um assistente especializado em análise de planos de estudo acadêmicos.

Analise o texto abaixo, que foi extraído de um PDF de plano de estudos, e extraia TODAS as informações relevantes.

IMPORTANTE:
1. Extraia TODOS os eventos (provas, trabalhos, entregas, apresentações, etc)
2. Identifique TODAS as matérias/disciplinas mencionadas
3. Se houver horários regulares de aulas, extraia
4. Se houver limites de falta, extraia
5. Se o ano não for mencionado, considere 2025
6. Normalize formatos de data variados
7. Para cada evento, tente identificar a matéria relacionada

Retorne APENAS um JSON válido seguindo EXATAMENTE esta estrutura:

{{
  "period": "2025.1",
  "subjects": [
    {{
      "name": "Nome Completo da Disciplina",
      "code": "COD123",
      "professor": "Nome do Professor",
      "total_hours": 60,
      "max_absences": 15,
      "schedule": {{
        "Segunda": ["08:00-10:00"],
        "Quarta": ["14:00-16:00"]
      }}
    }}
  ],
  "events": [
    {{
      "date": "2025-10-20",
      "time": "09:00",
      "title": "Prova de Cálculo I",
      "description": "Conteúdo: Derivadas e Integrais",
      "event_type": "prova",
      "subject": "Cálculo I",
      "location": "Sala 301",
      "priority": 5
    }}
  ]
}}

TIPOS DE EVENTOS VÁLIDOS:
- prova
- trabalho
- entrega
- revisao
- aula
- outro

PRIORIDADE (1-5):
- 5: Provas
- 4: Entregas de trabalhos
- 3: Apresentações
- 2: Revisões
- 1: Outros

TEXTO DO PDF:
---
{pdf_text}
---

RESPONDA APENAS COM O JSON, SEM TEXTO ADICIONAL.
"""
    
    @classmethod
    def analyze_study_plan(cls, pdf_text: str) -> Optional[Dict[str, Any]]:
        """
        Analisa texto do PDF e extrai eventos e matérias
        Suporta: Google Gemini (recomendado), OpenAI API ou LM Studio (local)
        
        Args:
            pdf_text: Texto extraído do PDF
            
        Returns:
            Dict com análise estruturada ou None se erro
        """
        # Determinar qual provider usar
        provider = getattr(settings, 'AI_PROVIDER', 'auto')
        gemini_key = getattr(settings, 'GOOGLE_GEMINI_KEY', '')
        openai_key = getattr(settings, 'OPENAI_API_KEY', '')
        base_url = getattr(settings, 'OPENAI_BASE_URL', None)
        
        # Auto-detectar provider
        if provider == 'auto':
            if gemini_key and GEMINI_AVAILABLE:
                provider = 'gemini'
            elif openai_key:
                provider = 'openai'
            elif base_url:
                provider = 'lmstudio'
            else:
                logger.error("Nenhum AI provider configurado!")
                return None
        
        # Usar provider selecionado
        if provider == 'gemini':
            return cls._analyze_with_gemini(pdf_text)
        elif provider in ['openai', 'lmstudio']:
            return cls._analyze_with_openai(pdf_text)
        else:
            logger.error(f"Provider inválido: {provider}")
            return None
    
    @classmethod
    def _analyze_with_gemini(cls, pdf_text: str) -> Optional[Dict[str, Any]]:
        """Análise usando Google Gemini"""
        if not GEMINI_AVAILABLE:
            logger.error("google-generativeai não instalado")
            return None
        
        gemini_key = getattr(settings, 'GOOGLE_GEMINI_KEY', '')
        if not gemini_key:
            logger.error("GOOGLE_GEMINI_KEY não configurada")
            return None
        
        try:
            # Configurar Gemini
            genai.configure(api_key=gemini_key)
            model_name = getattr(settings, 'GOOGLE_GEMINI_MODEL', 'gemini-2.5-flash')
            model = genai.GenerativeModel(model_name)
            
            logger.info(f"Usando Google Gemini: {model_name}")
            
            # Limitar tamanho do texto
            max_chars = 15000  # Gemini suporta mais que GPT-4
            if len(pdf_text) > max_chars:
                logger.warning(f"Texto muito longo ({len(pdf_text)} chars), truncando")
                pdf_text = pdf_text[:max_chars] + "\n\n[...texto truncado...]"
            
            # Preparar prompt
            prompt = cls.PROMPT_TEMPLATE.format(pdf_text=pdf_text)
            
            # Chamar Gemini
            response = model.generate_content(prompt)
            raw_response = response.text
            
            logger.info(f"Resposta recebida do Gemini: {len(raw_response)} caracteres")
            
            # Parsear JSON
            try:
                # Limpar resposta (remover markdown se houver)
                cleaned = cls._clean_json_response(raw_response)
                if cleaned:
                    raw_response = cleaned
                
                analysis = json.loads(raw_response)
                logger.info("JSON parseado com sucesso")
                
                # Validar estrutura
                if not cls._validate_analysis(analysis):
                    logger.error("Estrutura do JSON inválida")
                    return None
                
                return {
                    'raw_response': raw_response,
                    'analysis': analysis
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON do Gemini: {e}")
                logger.error(f"Resposta: {raw_response[:500]}")
                return None
        
        except Exception as e:
            logger.error(f"Erro ao chamar Gemini API: {e}")
            return None
    
    @classmethod
    def _analyze_with_openai(cls, pdf_text: str) -> Optional[Dict[str, Any]]:
        """Análise usando OpenAI ou LM Studio"""
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        base_url = getattr(settings, 'OPENAI_BASE_URL', None)
        
        try:
            # Configurar cliente OpenAI
            client_params = {}
            
            if base_url:
                # LM Studio ou API customizada
                logger.info(f"Usando API customizada: {base_url}")
                client_params['base_url'] = base_url
                client_params['api_key'] = api_key or 'lm-studio'  # LM Studio não precisa de key real
            else:
                # OpenAI oficial
                logger.info("Usando OpenAI API oficial")
                client_params['api_key'] = api_key
            
            client = openai.OpenAI(**client_params)
            
            # Limitar tamanho do texto (GPT-4 tem limite de tokens)
            max_chars = 12000  # ~3000 tokens
            if len(pdf_text) > max_chars:
                logger.warning(f"Texto muito longo ({len(pdf_text)} chars), truncando para {max_chars}")
                pdf_text = pdf_text[:max_chars] + "\n\n[...texto truncado...]"
            
            # Preparar prompt
            prompt = cls.PROMPT_TEMPLATE.format(pdf_text=pdf_text)
            
            # Determinar modelo
            model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
            logger.info(f"Enviando requisição para modelo: {model}")
            
            # Chamar API
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em extrair informações de planos de estudo. Sempre responda com JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Baixa temperatura para respostas mais consistentes
                max_tokens=2000
            )
            
            # Extrair resposta
            raw_response = response.choices[0].message.content
            logger.info(f"Resposta recebida: {len(raw_response)} caracteres")
            
            # Parsear JSON
            try:
                analysis = json.loads(raw_response)
                logger.info("JSON parseado com sucesso")
                
                # Validar estrutura
                if not cls._validate_analysis(analysis):
                    logger.error("Estrutura do JSON inválida")
                    return None
                
                return {
                    'raw_response': raw_response,
                    'analysis': analysis
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON da IA: {e}")
                logger.error(f"Resposta da IA: {raw_response[:500]}")
                
                # Tentar limpar a resposta
                cleaned = cls._clean_json_response(raw_response)
                if cleaned:
                    try:
                        analysis = json.loads(cleaned)
                        return {
                            'raw_response': raw_response,
                            'analysis': analysis
                        }
                    except:
                        pass
                
                return None
        
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI API: {e}")
            return None
    
    @staticmethod
    def _validate_analysis(analysis: Dict) -> bool:
        """Valida estrutura básica da análise"""
        required_keys = ['subjects', 'events']
        
        for key in required_keys:
            if key not in analysis:
                logger.error(f"Chave '{key}' faltando na análise")
                return False
        
        if not isinstance(analysis['subjects'], list):
            logger.error("'subjects' deve ser uma lista")
            return False
        
        if not isinstance(analysis['events'], list):
            logger.error("'events' deve ser uma lista")
            return False
        
        return True
    
    @staticmethod
    def _clean_json_response(response: str) -> Optional[str]:
        """Tenta limpar resposta da IA para obter JSON válido"""
        try:
            # Remover markdown code blocks
            if '```json' in response:
                response = response.split('```json')[1]
                response = response.split('```')[0]
            elif '```' in response:
                response = response.split('```')[1]
                response = response.split('```')[0]
            
            return response.strip()
        except:
            return None

