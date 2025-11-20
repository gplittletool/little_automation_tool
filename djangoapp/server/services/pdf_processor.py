"""
Serviço de processamento de PDFs
"""
import logging
from typing import Optional
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Processa PDFs e extrai texto"""
    
    @staticmethod
    def extract_text(pdf_path: str) -> Optional[str]:
        """
        Extrai todo o texto de um PDF
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            String com todo o texto ou None se erro
        """
        try:
            reader = PdfReader(pdf_path)
            text = ""
            
            # Extrair texto de todas as páginas
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                except Exception as e:
                    logger.warning(f"Erro ao extrair texto da página: {e}")
                    continue
            
            if not text.strip():
                logger.error("Nenhum texto extraído do PDF")
                return None
            
            logger.info(f"Texto extraído com sucesso: {len(text)} caracteres")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Erro ao processar PDF: {e}")
            return None
    
    @staticmethod
    def validate_pdf(file_obj) -> tuple[bool, str]:
        """
        Valida se o arquivo é um PDF válido
        
        Args:
            file_obj: Objeto de arquivo Django
            
        Returns:
            Tuple (is_valid, error_message)
        """
        # Verificar extensão
        if not file_obj.name.lower().endswith('.pdf'):
            return False, "O arquivo deve ser um PDF"
        
        # Verificar tamanho (máximo 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_obj.size > max_size:
            return False, f"Arquivo muito grande. Máximo: {max_size / (1024*1024):.0f}MB"
        
        # Verificar se não está vazio
        if file_obj.size == 0:
            return False, "Arquivo está vazio"
        
        try:
            # Tentar ler o PDF
            reader = PdfReader(file_obj)
            if len(reader.pages) == 0:
                return False, "PDF não contém páginas"
            
            return True, ""
            
        except Exception as e:
            return False, f"PDF inválido ou corrompido: {str(e)}"

