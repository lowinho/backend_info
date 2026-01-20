import pandas as pd
import spacy
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class PIIDetector:
    """
    Detector de PII V3.1 - Correção de Pipeline
    Modo Alta Precisão com correção para compatibilidade de versões do Spacy.
    """
    
    # Classificação conforme LGPD
    PII_TYPES = {
        # --- Dados Pessoais (Identificação) ---
        'CPF': 'CPF',
        'CNPJ': 'CNPJ',
        'RG': 'RG',
        'EMAIL': 'E-mail Pessoal',
        'PHONE': 'Telefone/Celular',
        'PERSON_NAME': 'Nome do Cidadão',
        'FULL_ADDRESS': 'Endereço Residencial Completo',
        'DOC_GENERICO': 'Outros Documentos (CNH/OAB/Título)',
        
        # --- Dados Sensíveis (Art. 5º LGPD) - CRÍTICOS ---
        'SENSITIVE_HEALTH': 'DADO SENSÍVEL: Saúde/Doença',
        'SENSITIVE_MINOR': 'DADO SENSÍVEL: Menor de Idade',
        'SENSITIVE_SOCIAL': 'DADO SENSÍVEL: Vulnerabilidade Social/Assistência'
    }

    # Palavras que a IA confunde com nomes, mas devem ser ignoradas
    NAME_BLOCKLIST = {
        'solicito', 'prezados', 'atenciosamente', 'bom', 'dia', 'tarde', 'noite',
        'segue', 'anexo', 'conforme', 'processo', 'sei', 'obrigado', 'grato',
        'senhor', 'senhora', 'secretaria', 'governo', 'distrito', 'federal',
        'defensoria', 'policia', 'civil', 'militar', 'bombeiro', 'justiça',
        'protocolo', 'cordialmente', 'respeitosamente', 'para', 'com', 'pelo',
        'informação', 'informações', 'acesso', 'cópia', 'vossa', 'senhoria'
    }

    def __init__(self):
        print("🔍 Inicializando PIIDetector V3.1 (Alta Precisão)...")
        try:
            # Tenta carregar o modelo grande
            self.nlp = spacy.load("pt_core_news_lg")
            
            # --- CORREÇÃO DO ERRO AQUI ---
            # Identifica quais componentes pesados existem no modelo atual
            # para desativá-los com segurança (acelera o processo)
            pipes_to_disable = ['parser', 'tagger', 'morphologizer', 'lemmatizer']
            existing_pipes = [p for p in pipes_to_disable if p in self.nlp.pipe_names]
            
            if existing_pipes:
                self.nlp.disable_pipes(existing_pipes)
                print(f"✅ Otimização: Componentes desativados para velocidade: {existing_pipes}")
                
        except OSError:
            print("⚠️ Modelo 'pt_core_news_lg' não encontrado. Usando regex puro.")
            self.nlp = None
        except Exception as e:
            print(f"⚠️ Erro ao carregar Spacy: {e}. Usando regex puro.")
            self.nlp = None

        # --- REGEX ESTRITO (Evita falsos positivos) ---
        self.regex_patterns = {
            # CPF: Exige formatação ou contexto muito claro de 11 digitos
            'CPF': r'(?:\b\d{3}\.\d{3}\.\d{3}-\d{2}\b)|(?<=CPF[:\s])\s*\d{11}',
            
            # CNPJ: Exige formatação
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            
            # Email: Bloqueia emails governamentais (ex: @df.gov.br)
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            
            # Telefone: Exige DDD e formato de celular/fixo
            'PHONE': r'\b(?:\(?[1-9]{2}\)?\s?)?(?:9\s?)?[5-9]\d{3}[-.\s]?\d{4}\b',
            
            # RG: Busca pelo contexto "RG:"
            'RG': r'(?i)(?:RG|Identidade)[:\s\.]+\d{1,10}',
            
            # Endereço Completo (Captura Rua, Quadra, Bloco, Lote)
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Quadra|Q\.|Qd\.|SQN|SQS|SHN|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.)\s+[A-Za-z0-9\s,.-]{5,50}\d+',
            
            # Documentos diversos
            'DOC_GENERICO': r'(?i)(?:OAB|CNH|Matr[íi]cula|NIS|PIS)[:\s\.]+\d{3,15}'
        }

        # --- CONTEXTO SENSÍVEL (LGPD ART 5) ---
        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [
                r'\bc[âa]ncer\b', r'\boncologia\b', r'\bhiv\b', r'\baids\b', 
                r'\basm[áa]tico\b', r'\bdoen[çc]a\b', r'\blaudo m[ée]dico\b', 
                r'\bCID\s?[A-Z]\d', r'\btranstorno\b', r'\bpsicol[óo]gic', 
                r'\bdepress[ãa]o\b', r'\bdefici[êe]ncia\b', r'\bautis'
            ],
            'SENSITIVE_MINOR': [
                r'\bmenor de idade\b', r'\bcrian[çc]a\b', r'\bfilh[ao] (?:de )?menor\b',
                r'\btutela\b', r'\bcreche\b', r'\balun[ao]\b'
            ],
            'SENSITIVE_SOCIAL': [
                r'\bvulnerabilidade\b', r'\baux[íi]lio emergencial\b', 
                r'\bcesta b[áa]sica\b', r'\bbolsa fam[íi]lia\b'
            ]
        }

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        if pd.isna(text) or not isinstance(text, str):
            return text, {}
        
        indices_to_mask = set()
        pii_stats = defaultdict(int)
        
        # 1. Regex Estrito (Alta confiança)
        for pii_type, pattern in self.regex_patterns.items():
            for match in re.finditer(pattern, text):
                indices_to_mask.update(range(match.start(), match.end()))
                pii_stats[pii_type] += 1

        # 2. Dados Sensíveis (Keywords)
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    indices_to_mask.update(range(match.start(), match.end()))
                    pii_stats[sens_type] += 1

        # 3. NLP para Nomes (Com Filtro de Blocklist)
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        name_candidate = ent.text.strip()
                        lower_name = name_candidate.lower()
                        
                        parts = lower_name.split()
                        
                        if (len(parts) >= 2 and 
                            not any(char.isdigit() for char in name_candidate) and
                            not any(p in self.NAME_BLOCKLIST for p in parts) and
                            len(name_candidate) > 4):
                            
                            match_range = set(range(ent.start_char, ent.end_char))
                            if not match_range.intersection(indices_to_mask):
                                indices_to_mask.update(match_range)
                                pii_stats['PERSON_NAME'] += 1
                                
            except Exception as e:
                # Silencia erros de NLP para não parar o processo
                pass

        # 4. Construção da Máscara
        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask:
                if char.isalnum():
                    redacted_chars.append('x')
                else:
                    redacted_chars.append(char)
            else:
                redacted_chars.append(char)
        
        return "".join(redacted_chars), dict(pii_stats)

    def get_pii_type_description(self, pii_type: str) -> str:
        return self.PII_TYPES.get(pii_type, pii_type)