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
    
    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI')
    DB_NAME = os.getenv('DB_NAME', 'lgpd_database')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'anonymized_data')
    REPORTS_COLLECTION = os.getenv('REPORTS_COLLECTION', 'processing_reports')
    ACCESS_INFO_COLLECTION = os.getenv('ACCESS_INFO_COLLECTION', 'access_info')  # Nova collection
    
    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB default
    ALLOWED_EXTENSIONS = {'csv', 'txt'}
    
    # Processing settings
    DEFAULT_CSV_COLUMN = os.getenv('DEFAULT_CSV_COLUMN', 'Texto Mascarado')
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 1000))
    
    ALLOWED_EXTENSIONS = {'txt', 'csv', 'xlsx', 'xls'}
    MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
    
    @staticmethod
    def validate():
        """Valida configurações críticas"""
        if not Config.MONGO_URI:
            raise ValueError("MONGO_URI não configurada no arquivo .env")
        if not Config.DB_NAME:
            raise ValueError("DB_NAME não configurada no arquivo .env")