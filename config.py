"""
Configurações centralizadas da aplicação
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações base da aplicação"""
    
    # Flask
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # MongoDB (Alinhado com o mongo_service.py novo)
    MONGO_URI = os.getenv('MONGO_URI')
    DB_NAME = os.getenv('DB_NAME', 'lgpd_database')
    
    # Collection para o relatório geral (Stats/Compliance)
    REPORTS_COLLECTION = os.getenv('REPORTS_COLLECTION', 'Acces_info_report')
    
    # Collection para os registros/mensagens individuais
    ACCESS_INFO_COLLECTION = os.getenv('ACCESS_INFO_COLLECTION', 'Access_info')
    
    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    
    # Mantenha apenas UMA definição aqui. 
    # Atualizei para suportar Excel (xlsx, xls) e fixei em 50MB (mais seguro que 10MB para planilhas grandes)
    ALLOWED_EXTENSIONS = {'txt', 'csv', 'xlsx', 'xls'}
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB

    # Processing settings
    DEFAULT_CSV_COLUMN = os.getenv('DEFAULT_CSV_COLUMN', 'Texto Mascarado')
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 1000))
    
    @staticmethod
    def validate():
        """Valida configurações críticas"""
        if not Config.MONGO_URI:
            raise ValueError("MONGO_URI não configurada no arquivo .env")
        if not Config.DB_NAME:
            raise ValueError("DB_NAME não configurada no arquivo .env")