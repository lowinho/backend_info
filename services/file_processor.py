"""
Processador de arquivos CSV e TXT
"""
import pandas as pd
import time
from typing import Dict, List
from collections import defaultdict
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
    
    def process_excel(self, file_path, process_uuid):
        start_time = time.time()
        
        # Lê o Excel usando Pandas
        # dtype=str garante que telefones/CPFs não percam zeros à esquerda
        df = pd.read_excel(file_path, dtype=str)
        
        # Tenta identificar a coluna de texto (ajuste conforme seu padrão)
        # Procura por colunas chamadas 'message', 'text', 'pedido', ou usa a primeira coluna
        target_col = None
        possible_cols = ['message', 'text', 'texto', 'pedido', 'descricao', 'Texto Mascarado']
        
        for col in df.columns:
            if col.lower() in [c.lower() for c in possible_cols]:
                target_col = col
                break
        
        if not target_col:
            target_col = df.columns[0] # Fallback: usa a primeira coluna

        records = []
        pii_stats = {}
        records_with_pii_count = 0

        # Itera sobre as linhas
        for index, row in df.iterrows():
            text = str(row[target_col]) if pd.notna(row[target_col]) else ""
            
            # Aplica a detecção e anonimização
            # Supõe que seu detector retorne { text: "...", detected: [...] } ou similar
            # Ajuste a chamada abaixo conforme seu PIIDetector real
            
            # Exemplo de uso baseado no script anterior:
            # Se detector.redact_text retorna só o texto, você precisará adaptar 
            # para ele retornar também o que achou se quiser estatísticas precisas.
            
            # Simulando chamada completa:
            analyzed = self.detector.analyze_and_redact(text) 
            # Se seu detector for simples, use: anonymized_text = self.detector.redact_text(text)
            
            # Monta o registro
            record = {
                'process_uuid': process_uuid,
                'original_id': str(row.get('id', index + 1)), # Tenta pegar ID do excel ou gera um
                'original_text': text, # Cuidado com LGPD ao salvar original
                'text_formatted': analyzed['redacted_text'],
                'mask_text': analyzed['redacted_text'], # Compatibilidade
                'detected_entities': analyzed['entities'],
                'processed_at': datetime.now().isoformat()
            }
            
            records.append(record)
            
            # Estatísticas
            if analyzed['entities']:
                records_with_pii_count += 1
                for ent_type in analyzed['entities']:
                    pii_stats[ent_type] = pii_stats.get(ent_type, 0) + 1

        processing_time = time.time() - start_time
        
        return {
            'records': records,
            'total_records': len(records),
            'records_with_pii': records_with_pii_count,
            'pii_stats': pii_stats,
            'processing_time': processing_time
        }