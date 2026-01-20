"""
Validadores de arquivos e dados
"""
import os
from typing import Set


def validate_file_extension(filename: str, allowed_extensions: Set[str]) -> str:
    """
    Valida extensão do arquivo
    
    Args:
        filename: Nome do arquivo
        allowed_extensions: Set de extensões permitidas
        
    Returns:
        Extensão do arquivo (sem ponto)
        
    Raises:
        FileValidationError: Se extensão não permitida
    """
    from utils.exceptions import FileValidationError
    
    if '.' not in filename:
        raise FileValidationError("Arquivo sem extensão")
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension not in allowed_extensions:
        raise FileValidationError(
            f"Extensão '{extension}' não permitida. "
            f"Permitidas: {', '.join(allowed_extensions)}"
        )
    
    return extension


def validate_file_size(file_path: str, max_size: int) -> bool:
    """
    Valida tamanho do arquivo
    
    Args:
        file_path: Caminho do arquivo
        max_size: Tamanho máximo em bytes
        
    Returns:
        True se válido
        
    Raises:
        FileValidationError: Se arquivo muito grande
    """
    from utils.exceptions import FileValidationError
    
    file_size = os.path.getsize(file_path)
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        raise FileValidationError(
            f"Arquivo muito grande: {file_mb:.2f}MB. Máximo permitido: {max_mb:.2f}MB"
        )
    
    return True


def validate_csv_structure(df) -> bool:
    """
    Valida estrutura básica do CSV
    
    Args:
        df: DataFrame pandas
        
    Returns:
        True se válido
        
    Raises:
        FileValidationError: Se estrutura inválida
    """
    from utils.exceptions import FileValidationError
    
    if df.empty:
        raise FileValidationError("Arquivo CSV está vazio")
    
    if len(df.columns) == 0:
        raise FileValidationError("CSV não possui colunas")
    
    return True