import pandas as pd
import time
from typing import Dict

class FileProcessor:
    """
    Processador V10.0 - Sincronizado com Terminal
    """
    
    # Lista de prioridade igual ao que você usaria no Terminal
    TARGET_COLUMNS_PRIORITY = [
        'texto mascarado', 'texto', 'conteudo', 'mensagem', 
        'descricao', 'text', 'content', 'description'
    ]

    def __init__(self, pii_detector):
        self.detector = pii_detector
    
    def _identify_text_column(self, df: pd.DataFrame) -> str:
        """
        Lógica Blindada de Seleção de Coluna:
        1. Tenta encontrar nomes exatos da lista de prioridade.
        2. Se não achar, pega a coluna de texto com maior média de caracteres (heurística).
        """
        # Normaliza colunas do DF para minúsculo para comparar
        df_cols_lower = {col.lower(): col for col in df.columns}
        
        # 1. Tentativa por nome (Prioridade)
        for target in self.TARGET_COLUMNS_PRIORITY:
            for col_lower, original_name in df_cols_lower.items():
                if target in col_lower:
                    print(f"[DEBUG] Coluna selecionada por nome: {original_name}")
                    return original_name
        
        # 2. Tentativa por tamanho do conteúdo (Heurística)
        best_col = None
        max_avg_len = 0
        
        for col in df.columns:
            if df[col].dtype == 'object': # Apenas colunas de texto
                try:
                    # Calcula média de tamanho ignorando nulos
                    avg_len = df[col].astype(str).str.len().mean()
                    if avg_len > max_avg_len:
                        max_avg_len = avg_len
                        best_col = col
                except:
                    continue
        
        if best_col:
            print(f"[DEBUG] Coluna selecionada por tamanho: {best_col}")
            return best_col
            
        # 3. Fallback final: primeira coluna
        return df.columns[0]

    def _process_dataframe(self, df: pd.DataFrame, process_uuid: str) -> Dict:
        start_time = time.time()
        
        # Identificação da coluna
        text_column = self._identify_text_column(df)
        print(f"[INFO] Processando coluna: '{text_column}' | Total linhas: {len(df)}")
        
        records = []
        pii_stats_global = {}
        total_invalid_cpfs = 0
        records_with_pii_count = 0  # <--- NOVO CONTADOR
        
        for idx, row in df.iterrows():
            original_text = str(row[text_column]) if pd.notna(row[text_column]) else ""
            
            redacted_text, pii_stats, invalid_count = self.detector.detect_and_redact(original_text)
            
            total_invalid_cpfs += invalid_count
            
            # Se encontrou qualquer PII nesta linha, incrementa o contador de REGISTROS
            if pii_stats:  # <--- LÓGICA CORRETA
                records_with_pii_count += 1
            
            for pii_type, count in pii_stats.items():
                pii_stats_global[pii_type] = pii_stats_global.get(pii_type, 0) + count
            
            if original_text.strip():
                records.append({
                    'process_uuid': process_uuid,
                    'record_id': idx + 1,
                    'original_text': original_text,
                    'redacted_text': redacted_text,
                    'pii_detected': pii_stats,
                    'has_pii': bool(pii_stats)
                })
        
        processing_time = time.time() - start_time
        
        return {
            'process_uuid': process_uuid,
            'total_records': len(records),
            'records': records,
            'pii_stats': pii_stats_global,
            'processing_time': processing_time,
            'invalid_cpf_count': total_invalid_cpfs,
            'records_with_pii_count': records_with_pii_count # <--- RETORNA O VALOR REAL
        }

    def process_csv(self, filepath: str, process_uuid: str) -> Dict:
        try:
            df = pd.read_csv(filepath)
        except:
            df = pd.read_csv(filepath, encoding='latin1')
        return self._process_dataframe(df, process_uuid)

    def process_excel(self, filepath: str, process_uuid: str) -> Dict:
        # Garante que lê Excel corretamente
        df = pd.read_excel(filepath)
        return self._process_dataframe(df, process_uuid)

    def process_txt(self, filepath: str, process_uuid: str) -> Dict:
        # Lê TXT como DataFrame de uma coluna
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        df = pd.DataFrame(lines, columns=['conteudo'])
        return self._process_dataframe(df, process_uuid)