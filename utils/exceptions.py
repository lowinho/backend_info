"""
Exceções customizadas da aplicação
"""


class PIIDetectionError(Exception):
    """Erro base para detecção de PII"""
    pass


class FileValidationError(Exception):
    """Erro de validação de arquivo"""
    pass


class ProcessingError(Exception):
    """Erro durante processamento"""
    pass


class DatabaseError(Exception):
    """Erro de banco de dados"""
    pass


class ConfigurationError(Exception):
    """Erro de configuração"""
    pass