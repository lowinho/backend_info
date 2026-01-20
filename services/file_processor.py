import pandas as pd
import time
from typing import Dict
from collections import defaultdict
from datetime import datetime
# from config import Config # Assumindo config existente

class FileProcessor:
    """Processa arquivos CSV e TXT para detecção e anonimização de PII"""
    
    def __init__(self, pii_detector):
        self.detector = pii_detector
        # self.default_column = Config.DEFAULT_CSV_COLUMN # Usar valor padrão se config não existir
        self.default_column = "texto" 
    
    def process_csv(self, file_path: str, process_uuid: str) -> Dict:
        # Mantém lógica original, apenas beneficia-se do novo detector
        return self._generic_process(file_path, process_uuid, 'csv')

    def process_excel(self, file_path: str, process_uuid: str) -> Dict:
        return self._generic_process(file_path, process_uuid, 'excel')

    def process_txt(self, file_path: str, process_uuid: str) -> Dict:
        # Lógica TXT simplificada
        return self._generic_process(file_path, process_uuid, 'txt')

    def _generic_process(self, file_path: str, process_uuid: str, file_type: str) -> Dict:
        """
        Método unificado para processamento para evitar duplicação de código
        """
        start_time = time.time()
        
        # Carregamento do arquivo
        if file_type == 'csv':
            df = pd.read_csv(file_path)
            text_column = self._identify_text_column(df)
        elif file_type == 'excel':
            df = pd.read_excel(file_path, dtype=str)
            text_column = self._identify_text_column(df)
            if not text_column and len(df.columns) > 0:
                text_column = df.columns[0]
        elif file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            df = pd.DataFrame(lines, columns=['texto_conteudo'])
            text_column = 'texto_conteudo'
        
        print(f"📝 Processando arquivo {file_type.upper()}. Coluna alvo: '{text_column}'")

        records = []
        pii_stats_total = defaultdict(int)
        records_with_pii = 0
        records_with_sensitive = 0 # Nova métrica
        
        for idx, row in df.iterrows():
            original_text = str(row[text_column]) if pd.notna(row[text_column]) else ""
            
            if not original_text or original_text == "nan":
                continue
            
            # Detectar e anonimizar
            anonymized_text, pii_stats = self.detector.detect_and_redact(original_text)
            
            has_pii = bool(pii_stats)
            # Verifica se tem dados sensíveis específicos
            is_sensitive = 'SENSITIVE_HEALTH' in pii_stats or 'MINOR_CONTEXT' in pii_stats
            
            if has_pii:
                records_with_pii += 1
                if is_sensitive:
                    records_with_sensitive += 1
                    
                for pii_type, count in pii_stats.items():
                    pii_stats_total[pii_type] += count
            
            # Preparar registro
            record = {
                'process_uuid': process_uuid,
                'record_id': str(idx),
                'original_id': str(row.get('ID', row.get('id', idx))),
                'mask_text': original_text,
                'text_formatted': anonymized_text,
                'pii_detected': pii_stats,
                'has_pii': has_pii,
                'is_sensitive': is_sensitive, # Nova flag no retorno
                'processed_at': datetime.now().isoformat()
            }
            
            # Metadados extras (apenas para excel/csv)
            if file_type != 'txt':
                for col in df.columns:
                    if col not in [text_column, 'ID', 'id']:
                         record[f'meta_{col}'] = str(row[col])

            records.append(record)
            
        processing_time = time.time() - start_time
        
        # Retorno mantendo nomenclatura original + novos contadores
        return {
            'records': records,
            'total_records': len(records),
            'records_with_pii': records_with_pii,
            'records_with_sensitive': records_with_sensitive, # Dado extra
            'pii_stats': dict(pii_stats_total),
            'processing_time': processing_time
        }

    def _identify_text_column(self, df: pd.DataFrame) -> str:
        # Mesma lógica original
        if self.default_column in df.columns:
            return self.default_column
        
        possible_cols = ['texto', 'text', 'mensagem', 'descricao', 'pedido', 'texto mascarado']
        for col in df.columns:
            if any(pc in col.lower() for pc in possible_cols):
                return col
                
        for col in df.columns:
            if df[col].dtype == 'object':
                sample = df[col].dropna().head(5)
                if len(sample) > 0 and sample.str.len().mean() > 10:
                    return col
        return None