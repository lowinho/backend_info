"""
File Processor - Atualizado para PIIDetector V10.0
Compatível com frontend existente + rastreamento de CPFs inválidos
"""
import pandas as pd
import time
from typing import Dict, List

class FileProcessor:
    """Processa arquivos e aplica detecção de PII"""
    
    def __init__(self, pii_detector):
        self.detector = pii_detector
    
    def process_csv(self, filepath: str, process_uuid: str) -> Dict:
        """
        Processa arquivo CSV
        Retorna estrutura compatível com API + dados de qualidade
        """
        start_time = time.time()
        
        df = pd.read_csv(filepath)
        total_records = len(df)
        
        # Identifica coluna de texto principal
        text_column = self._identify_text_column(df)
        if not text_column:
            raise ValueError("Nenhuma coluna de texto identificada")
        
        # Processamento com rastreamento de CPFs inválidos
        records = []
        pii_stats_global = {}
        total_invalid_cpfs = 0  # NOVO: Rastreamento de CPFs inválidos
        
        for idx, row in df.iterrows():
            original_text = str(row[text_column])
            
            # Aplica detecção (mantém compatibilidade)
            redacted_text, pii_stats = self.detector.detect_and_redact(original_text)
            
            # NOVO: Captura CPFs inválidos da última execução
            invalid_cpf_count = self.detector.get_last_invalid_cpf_count()
            total_invalid_cpfs += invalid_cpf_count
            
            # Acumula estatísticas globais
            for pii_type, count in pii_stats.items():
                pii_stats_global[pii_type] = pii_stats_global.get(pii_type, 0) + count
            
            # Monta registro (estrutura original do frontend)
            record = {
                'process_uuid': process_uuid,
                'record_id': idx + 1,
                'original_text': original_text,
                'redacted_text': redacted_text,
                'pii_detected': pii_stats,
                'has_pii': bool(pii_stats)
            }
            records.append(record)
        
        processing_time = time.time() - start_time
        
        # Retorna estrutura compatível + dados adicionais
        return {
            'process_uuid': process_uuid,
            'total_records': total_records,
            'records': records,
            'pii_stats': pii_stats_global,
            'processing_time': processing_time,
            'invalid_cpf_count': total_invalid_cpfs  # NOVO: Campo adicional
        }
    
    def process_txt(self, filepath: str, process_uuid: str) -> Dict:
        """
        Processa arquivo TXT (linha por linha)
        """
        start_time = time.time()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        records = []
        pii_stats_global = {}
        total_invalid_cpfs = 0
        
        for idx, line in enumerate(lines):
            original_text = line.strip()
            if not original_text:
                continue
            
            redacted_text, pii_stats = self.detector.detect_and_redact(original_text)
            invalid_cpf_count = self.detector.get_last_invalid_cpf_count()
            total_invalid_cpfs += invalid_cpf_count
            
            for pii_type, count in pii_stats.items():
                pii_stats_global[pii_type] = pii_stats_global.get(pii_type, 0) + count
            
            record = {
                'process_uuid': process_uuid,
                'record_id': idx + 1,
                'original_text': original_text,
                'redacted_text': redacted_text,
                'pii_detected': pii_stats,
                'has_pii': bool(pii_stats)
            }
            records.append(record)
        
        processing_time = time.time() - start_time
        
        return {
            'process_uuid': process_uuid,
            'total_records': len(records),
            'records': records,
            'pii_stats': pii_stats_global,
            'processing_time': processing_time,
            'invalid_cpf_count': total_invalid_cpfs
        }
    
    def process_excel(self, filepath: str, process_uuid: str) -> Dict:
        """
        Processa arquivo Excel (XLSX/XLS)
        """
        start_time = time.time()
        
        df = pd.read_excel(filepath)
        total_records = len(df)
        
        text_column = self._identify_text_column(df)
        if not text_column:
            raise ValueError("Nenhuma coluna de texto identificada")
        
        records = []
        pii_stats_global = {}
        total_invalid_cpfs = 0
        
        for idx, row in df.iterrows():
            original_text = str(row[text_column])
            
            redacted_text, pii_stats = self.detector.detect_and_redact(original_text)
            invalid_cpf_count = self.detector.get_last_invalid_cpf_count()
            total_invalid_cpfs += invalid_cpf_count
            
            for pii_type, count in pii_stats.items():
                pii_stats_global[pii_type] = pii_stats_global.get(pii_type, 0) + count
            
            record = {
                'process_uuid': process_uuid,
                'record_id': idx + 1,
                'original_text': original_text,
                'redacted_text': redacted_text,
                'pii_detected': pii_stats,
                'has_pii': bool(pii_stats)
            }
            records.append(record)
        
        processing_time = time.time() - start_time
        
        return {
            'process_uuid': process_uuid,
            'total_records': total_records,
            'records': records,
            'pii_stats': pii_stats_global,
            'processing_time': processing_time,
            'invalid_cpf_count': total_invalid_cpfs
        }
    
    def _identify_text_column(self, df: pd.DataFrame) -> str:
        """
        Identifica coluna principal de texto
        Heurística: maior coluna com tipo object e média de caracteres > 20
        """
        for col in df.columns:
            if df[col].dtype == 'object':
                avg_length = df[col].astype(str).str.len().mean()
                if avg_length > 20:
                    return col
        return None