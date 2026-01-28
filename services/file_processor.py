import pandas as pd
import time
from datetime import datetime
from collections import defaultdict

class FileProcessor:
    def __init__(self, detector):
        self.detector = detector

    def process_excel(self, filepath, process_uuid):
        try:
            start_time = time.time()
            df = pd.read_excel(filepath)
            
            # Limpeza básica e identificação da coluna alvo
            df.columns = [c.strip() for c in df.columns]
            target_col = 'Texto Mascarado' # Fallback ou lógica de detecção dinâmica pode vir aqui
            
            # Se não achar a coluna exata, tenta achar uma parecida
            if target_col not in df.columns:
                 for col in df.columns:
                    if 'texto' in col.lower() or 'conteudo' in col.lower() or 'descri' in col.lower():
                        target_col = col
                        break

            processed_records = []
            pii_stats_total = defaultdict(int)
            invalid_cpf_total = 0
            records_with_pii_count = 0  # <--- CONTADOR IMPORTANTE

            # Processamento linha a linha
            for idx, row in df.iterrows():
                # Tenta pegar ID, se não tiver gera um
                record_id = row.get('ID', row.get('id', row.get('Protocolo', f'Linha_{idx+2}')))
                
                text_content = str(row[target_col]) if target_col in df.columns else ""
                
                # CHAMA O DETECTOR NOVO
                redacted_text, stats, invalid_stats = self.detector.detect_and_redact(text_content)
                
                # Se detectou PII nesta linha
                if stats:
                    records_with_pii_count += 1
                    for k, v in stats.items():
                        pii_stats_total[k] += v
                
                if 'CPF_INVALID' in invalid_stats:
                    invalid_cpf_total += invalid_stats['CPF_INVALID']

                # Monta o objeto para salvar no Mongo
                record_data = {
                    'process_uuid': process_uuid,
                    'record_id': str(record_id),
                    'original_text': text_content, # Cuidado com LGPD aqui em produção
                    'redacted_text': redacted_text,
                    'pii_detected': stats,
                    'has_pii': bool(stats),
                    'processed_at': datetime.now()
                }
                processed_records.append(record_data)

            return {
                'total_records': len(df),
                'pii_stats': dict(pii_stats_total),
                'processing_time': time.time() - start_time,
                'records': processed_records,
                'invalid_cpf_count': invalid_cpf_total,
                'records_with_pii_count': records_with_pii_count # <--- RETORNO CORRETO
            }

        except Exception as e:
            raise Exception(f"Erro ao processar Excel: {str(e)}")

    # (Você deve replicar a lógica do records_with_pii_count para process_csv e process_txt também)