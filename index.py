import pandas as pd
import spacy
import re
import os
from database import MongoService

# --- Configuration ---
FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
TARGET_COLUMN = 'Texto Mascarado' 

class PIIDetector:
    def __init__(self):
        print("--- Initializing AI Model ---")
        try:
            # Carrega o modelo de NLP em português
            self.nlp = spacy.load("pt_core_news_lg")
        except OSError:
            print("ERROR: Language model not found. Run: python -m spacy download pt_core_news_lg")
            exit()
            
        # Padrões Regex para dados estruturados
        self.regex_patterns = {
            'CPF': r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',
            'CNPJ': r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b(?:\(?\d{2}\)?\s?)?(?:9\d{4}|\d{4})[-.\s]?\d{4}\b',
            'SEI_PROCESS': r'\b\d{5}-?\d{6,}/?\d{4}-?\d{2}\b'
        }

    def redact_text(self, text):
        """
        Detecta dados sensíveis e substitui letras/números por 'x',
        mantendo a pontuação original.
        """
        if pd.isna(text) or not isinstance(text, str):
            return text
            
        indices_to_mask = set()
        
        # 1. Regex Scan (Padrões fixos)
        for pattern in self.regex_patterns.values():
            for match in re.finditer(pattern, text):
                indices_to_mask.update(range(match.start(), match.end()))

        # 2. NLP Scan (Nomes de Pessoas)
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PER" and len(ent.text.split()) > 1:
                indices_to_mask.update(range(ent.start_char, ent.end_char))
        
        # 3. Reconstrução com máscara 'x'
        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask and char.isalnum():
                redacted_chars.append('x')
            else:
                redacted_chars.append(char)
                
        return "".join(redacted_chars)

# --- Fluxo Principal de Execução ---
if __name__ == "__main__":
    # 1. Validação do Arquivo
    if not os.path.exists(FILE_NAME):
        print(f"ERRO: Arquivo '{FILE_NAME}' não encontrado.")
        exit()

    # 2. Leitura do Excel
    print(f"Lendo Excel: {FILE_NAME}...")
    df = pd.read_excel(FILE_NAME)

    if TARGET_COLUMN not in df.columns:
        print(f"ERRO: Coluna '{TARGET_COLUMN}' não encontrada no Excel.")
        exit()

    # 3. Inicialização dos Serviços
    detector = PIIDetector()
    
    # 4. Processamento (Anonimização)
    print("Processando lógica de anonimização...")
    
    # Cria a coluna anonimizada
    df['Texto_Anonimizado'] = df[TARGET_COLUMN].apply(detector.redact_text)
    
    # Adiciona data de processamento
    df['proccess_date'] = pd.Timestamp.now()

    # --- NOVO: Renomeação e Preparação para o Mongo ---
    print("Formatando colunas para o padrão da API...")
    
    # Aqui renomeamos as colunas para bater com o Schema do Mongoose/Node.js
    df_mongo = df.rename(columns={
        'ID': 'id',
        'Texto Mascarado': 'mask_text', # ID -> id
        'Texto_Anonimizado': 'text_formatted' # Texto_Anonimizado -> text_formatted
    })

    # Opcional: Se quiser enviar APENAS os campos que a API usa, descomente a linha abaixo:
    # df_mongo = df_mongo[['id', 'text_formatted', 'data_processamento', 'Texto Mascarado']]

    # 5. Salvar no MongoDB
    print("Preparando envio para o MongoDB...")
    
    # Converte para lista de dicionários (JSON)
    records = df_mongo.to_dict(orient='records')
    
    try:
        mongo = MongoService()
        mongo.save_batch(records)
        mongo.close()
    except Exception as e:
        print("Pulei a etapa do banco devido a erro de conexão (verifique o .env ou o Docker).")
        
    print("--- Processo Finalizado com Sucesso ---")