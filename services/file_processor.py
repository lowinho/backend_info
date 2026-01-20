"""
Processador de arquivos CSV e TXT
"""
import pandas as pd
import time
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
from config import Config


class FileProcessor:
    """Processa arquivos CSV e TXT para detecção e anonimização de PII"""
    
    def __init__(self, pii_detector):
        """
        Args:
            pii_detector: Instância do PIIDetector
        """
        self.detector = pii_detector
        self.default_column = Config.DEFAULT_CSV_COLUMN
    
    def process_csv(self, file_path: str, process_uuid: str) -> Dict:
        """
        Processa arquivo CSV
        
        Args:
            file_path: Caminho do arquivo CSV
            process_uuid: UUID do processamento
            
        Returns:
            Dicionário com records processados e estatísticas
        """
        start_time = time.time()
        
        # Ler CSV
        df = pd.read_csv(file_path)
        
        # Identificar coluna de texto
        text_column = self._identify_text_column(df)
        
        if not text_column:
            raise ValueError(
                f"Coluna de texto não encontrada. "
                f"Esperado: '{self.default_column}' ou coluna com 'texto/text'"
            )
        
        print(f"📝 Processando coluna: '{text_column}'")
        
        # Processar registros
        records = []
        pii_stats_total = defaultdict(int)
        records_with_pii = 0
        
        for idx, row in df.iterrows():
            original_text = row[text_column]
            
            # Detectar e anonimizar
            anonymized_text, pii_stats = self.detector.detect_and_redact(original_text)
            
            # Contabilizar estatísticas
            if pii_stats:
                records_with_pii += 1
                for pii_type, count in pii_stats.items():
                    pii_stats_total[pii_type] += count
            
            # Preparar registro para MongoDB
            record = {
                'process_uuid': process_uuid,
                'record_id': str(idx),
                'original_id': row.get('ID', idx),  # Mantém ID original se existir
                'mask_text': str(original_text),
                'text_formatted': anonymized_text,
                'pii_detected': pii_stats,
                'has_pii': bool(pii_stats),
                'processed_at': pd.Timestamp.now().isoformat()
            }
            
            # Adicionar outras colunas do CSV
            for col in df.columns:
                if col not in [text_column, 'ID']:
                    record[f'meta_{col}'] = row[col]
            
            records.append(record)
        
        processing_time = time.time() - start_time
        
        return {
            'records': records,
            'total_records': len(records),
            'records_with_pii': records_with_pii,
            'pii_stats': dict(pii_stats_total),
            'processing_time': processing_time
        }
    
    def process_txt(self, file_path: str, process_uuid: str) -> Dict:
        """
        Processa arquivo TXT (uma linha = um registro)
        
        Args:
            file_path: Caminho do arquivo TXT
            process_uuid: UUID do processamento
            
        Returns:
            Dicionário com records processados e estatísticas
        """
        start_time = time.time()
        
        # Ler arquivo de texto
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"📝 Processando {len(lines)} linhas do arquivo TXT")
        
        records = []
        pii_stats_total = defaultdict(int)
        records_with_pii = 0
        
        for idx, line in enumerate(lines):
            line = line.strip()
            
            if not line:  # Pular linhas vazias
                continue
            
            # Detectar e anonimizar
            anonymized_text, pii_stats = self.detector.detect_and_redact(line)
            
            # Contabilizar estatísticas
            if pii_stats:
                records_with_pii += 1
                for pii_type, count in pii_stats.items():
                    pii_stats_total[pii_type] += count
            
            # Preparar registro para MongoDB
            record = {
                'process_uuid': process_uuid,
                'record_id': str(idx),
                'line_number': idx + 1,
                'mask_text': line,
                'text_formatted': anonymized_text,
                'pii_detected': pii_stats,
                'has_pii': bool(pii_stats),
                'processed_at': pd.Timestamp.now().isoformat()
            }
            
            records.append(record)
        
        processing_time = time.time() - start_time
        
        return {
            'records': records,
            'total_records': len(records),
            'records_with_pii': records_with_pii,
            'pii_stats': dict(pii_stats_total),
            'processing_time': processing_time
        }
    
    def process_excel(self, file_path: str, process_uuid: str) -> Dict:
        """
        Processa arquivo Excel (.xlsx ou .xls)
        
        Args:
            file_path: Caminho do arquivo Excel
            process_uuid: UUID do processamento
            
        Returns:
            Dicionário com records processados e estatísticas
        """
        start_time = time.time()
        
        # Ler Excel mantendo tipos originais (dtype=str preserva zeros à esquerda em CPF/telefone)
        df = pd.read_excel(file_path, dtype=str)
        
        print(f"📝 Processando arquivo Excel com {len(df)} linhas")
        
        # Identificar coluna de texto
        text_column = self._identify_text_column(df)
        
        if not text_column:
            # Se não encontrar, tenta colunas comuns de Excel
            possible_cols = ['message', 'texto', 'pedido', 'descricao', 'texto mascarado']
            for col in df.columns:
                if col.lower().strip() in possible_cols:
                    text_column = col
                    break
            
            # Se ainda não encontrou, usa a primeira coluna
            if not text_column and len(df.columns) > 0:
                text_column = df.columns[0]
                print(f"⚠️  Usando primeira coluna como padrão: '{text_column}'")
        
        if not text_column:
            raise ValueError("Não foi possível identificar coluna de texto no arquivo Excel")
        
        print(f"📝 Processando coluna: '{text_column}'")
        
        # Processar registros
        records = []
        pii_stats_total = defaultdict(int)
        records_with_pii = 0
        
        for idx, row in df.iterrows():
            # Pega o texto da coluna identificada
            original_text = str(row[text_column]) if pd.notna(row[text_column]) else ""
            
            if not original_text or original_text == "nan":
                continue  # Pula linhas vazias
            
            # Detectar e anonimizar usando o método correto
            anonymized_text, pii_stats = self.detector.detect_and_redact(original_text)
            
            # Contabilizar estatísticas
            if pii_stats:
                records_with_pii += 1
                for pii_type, count in pii_stats.items():
                    pii_stats_total[pii_type] += count
            
            # Preparar registro para MongoDB
            record = {
                'process_uuid': process_uuid,
                'record_id': str(idx),
                'original_id': row.get('id', row.get('ID', idx)),  # Tenta pegar ID do Excel
                'mask_text': original_text,
                'text_formatted': anonymized_text,
                'pii_detected': pii_stats,
                'has_pii': bool(pii_stats),
                'processed_at': datetime.now().isoformat()
            }
            
            # Adicionar outras colunas do Excel como metadados
            for col in df.columns:
                if col not in [text_column, 'id', 'ID']:
                    value = row[col]
                    if pd.notna(value):
                        record[f'meta_{col}'] = str(value)
            
            records.append(record)
        
        processing_time = time.time() - start_time
        
        return {
            'records': records,
            'total_records': len(records),
            'records_with_pii': records_with_pii,
            'pii_stats': dict(pii_stats_total),
            'processing_time': processing_time
        }
    
    def _identify_text_column(self, df: pd.DataFrame) -> str:
        """
        Identifica automaticamente a coluna de texto no DataFrame
        
        Prioridade:
        1. Coluna configurada (DEFAULT_CSV_COLUMN)
        2. Colunas contendo 'texto' ou 'text'
        3. Primeira coluna string com valores significativos
        """
        # Verificar coluna padrão
        if self.default_column in df.columns:
            return self.default_column
        
        # Buscar por nome parcial
        for col in df.columns:
            if 'texto' in col.lower() or 'text' in col.lower():
                return col
        
        # Última opção: primeira coluna tipo string
        for col in df.columns:
            if df[col].dtype == 'object':
                # Verificar se tem conteúdo significativo
                sample = df[col].dropna().head(5)
                if len(sample) > 0 and sample.str.len().mean() > 10:
                    return col
        
        return None