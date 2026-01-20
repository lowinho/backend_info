import pandas as pd
import spacy
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class PIIDetector:
    """
    Detector de PII V6.0 - Validação por Dicionário (IBGE)
    Foco: Precisão Extrema em Nomes. Só aceita se tiver estrutura Nome + Sobrenome
    e contiver elementos comuns da onomástica brasileira.
    """
    
    PII_TYPES = {
        'CPF': 'CPF',
        'CNPJ': 'CNPJ',
        'RG': 'RG',
        'EMAIL': 'E-mail Pessoal',
        'PHONE': 'Telefone/Celular',
        'PERSON_NAME': 'Nome Próprio (Validado)',
        'FULL_ADDRESS': 'Endereço Residencial',
        'DOC_GENERICO': 'Outros Documentos',
        'SENSITIVE_HEALTH': 'DADO SENSÍVEL: Saúde',
        'SENSITIVE_MINOR': 'DADO SENSÍVEL: Menor',
        'SENSITIVE_SOCIAL': 'DADO SENSÍVEL: Social'
    }

    # --- BASE DE CONHECIMENTO (TOP NOMES/SOBRENOMES BRASIL - Fonte: IBGE) ---
    # Usado para validar se o que a IA achou é realmente um nome de pessoa
    COMMON_NAMES = {
        'maria', 'joao', 'ana', 'carlos', 'paulo', 'jose', 'lucas', 'pedro',
        'marcos', 'luiz', 'gabriel', 'rafael', 'francisco', 'marcelo', 'bruno',
        'felipe', 'guilherme', 'rodrigo', 'antonio', 'mateus', 'andre', 'fernando',
        'fabio', 'leonardo', 'gustavo', 'juliana', 'patricia', 'aline', 'camila',
        'bruna', 'jessica', 'leticia', 'julia', 'luciana', 'amanda', 'mariana',
        'vanessa', 'alice', 'beatriz', 'larissa', 'debora', 'claudia', 'carol',
        'carolina', 'sandra', 'regina', 'roberta', 'edson', 'sergio', 'vitor',
        'thiago', 'alexandre', 'eduardo', 'daniel', 'renato', 'ricardo', 'jorge',
        'samuel', 'diego', 'leandro', 'tiago', 'anderson', 'claudio', 'marcio',
        'mauro', 'roberto', 'wellington', 'wallace', 'robson', 'cristiano',
        'geraldo', 'raimundo', 'sebastiao', 'miguel', 'arthur', 'heitor', 'bernardo',
        'davi', 'theo', 'lorenzo', 'gabriel', 'gael', 'bento', 'helena', 'laura',
        'sophia', 'manuela', 'maite', 'liz', 'cecilia', 'elisa', 'maitê', 'eloá'
    }

    COMMON_SURNAMES = {
        'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira', 'alves',
        'pereira', 'lima', 'gomes', 'costa', 'ribeiro', 'martins', 'carvalho',
        'almeida', 'lopes', 'soares', 'fernandes', 'vieira', 'barbosa', 'rocha',
        'dias', 'nascimento', 'andrade', 'moreira', 'nunes', 'marques', 'machado',
        'mendes', 'freitas', 'cardoso', 'ramos', 'goncalves', 'santana', 'teixeira',
        'cavalcanti', 'moura', 'campos', 'jesus', 'pinto', 'araujo', 'leite',
        'barros', 'farias', 'cunha', 'reis', 'siqueira', 'moraes', 'castro',
        'batista', 'neves', 'rosa', 'medeiros', 'dantas', 'conceicao', 'braga',
        'filho', 'neto', 'junior', 'sobrinho', 'mota', 'vasconcelos', 'cruz',
        'viana', 'peixoto', 'maia', 'monteiro', 'coelho', 'correia', 'brito'
    }

    def __init__(self):
        print("🔍 Inicializando PIIDetector V6.0 (Validação IBGE)...")
        try:
            self.nlp = spacy.load("pt_core_news_lg")
            # Otimização
            pipes_to_disable = ['parser', 'tagger', 'morphologizer', 'lemmatizer']
            existing_pipes = [p for p in pipes_to_disable if p in self.nlp.pipe_names]
            if existing_pipes:
                self.nlp.disable_pipes(existing_pipes)
        except:
            print("⚠️ Erro NLP. Usando apenas Regex.")
            self.nlp = None

        self.phone_patterns = [
            r'\b(?:\(?\d{2}\)?\s?)?(?:9\s?)?[5-9]\d{3}[-.\s]\d{4}\b',
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,12}\b'
        ]

        self.regex_patterns = {
            'CPF': r'(?:\b\d{3}\.\d{3}\.\d{3}-\d{2}\b)|(?<=CPF[:\s])\s*\d{11}',
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|SRES|SHDF|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.)\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            'DOC_GENERICO': r'(?i)(?:OAB|CNH|Matr[íi]cula|NIS|PIS)[:\s\.]+\d{3,15}',
            'RG': r'(?i)(?:RG|Identidade)[:\s\.]+\d{1,10}'
        }

        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [r'\bc[âa]ncer\b', r'\boncologia\b', r'\bhiv\b', r'\baids\b', r'\basm[áa]tico\b', r'\bminha doen[çc]a\b', r'\blaudo m[ée]dico\b', r'\bCID\s?[A-Z]\d', r'\btranstorno\b', r'\bdepress[ãa]o\b', r'\bdefici[êe]ncia\b', r'\bautis'],
            'SENSITIVE_MINOR': [r'\bmenor de idade\b', r'\bcrian[çc]a\b', r'\bfilh[ao] (?:de )?menor\b', r'\btutela\b', r'\bcreche\b', r'\balun[ao]\b'],
            'SENSITIVE_SOCIAL': [r'\bvulnerabilidade\b', r'\baux[íi]lio emergencial\b', r'\bcesta b[áa]sica\b', r'\bbolsa fam[íi]lia\b']
        }

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        if pd.isna(text) or not isinstance(text, str):
            return text, {}
        
        indices_to_mask = set()
        pii_stats = defaultdict(int)
        
        # 1. Regex Padrão
        for pii_type, pattern in self.regex_patterns.items():
            for match in re.finditer(pattern, text):
                indices_to_mask.update(range(match.start(), match.end()))
                pii_stats[pii_type] += 1

        # 2. Telefones (Híbrido)
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text):
                match_range = set(range(match.start(), match.end()))
                if not match_range.intersection(indices_to_mask):
                    indices_to_mask.update(match_range)
                    pii_stats['PHONE'] += 1

        # 3. Sensíveis
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    indices_to_mask.update(range(match.start(), match.end()))
                    pii_stats[sens_type] += 1

        # 4. NLP COM VALIDAÇÃO DE DICIONÁRIO (A Grande Mudança)
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        name_candidate = ent.text.strip()
                        clean_name = re.sub(r'[^\w\s]', '', name_candidate.lower())
                        parts = clean_name.split()
                        
                        # --- REGRA 1: Estrutura (Pelo menos 2 nomes) ---
                        if len(parts) < 2:
                            continue
                        
                        # --- REGRA 2: Validação Cruzada (IBGE) ---
                        # Para ser um nome, pelo menos uma das partes TEM que ser 
                        # um nome ou sobrenome comum brasileiro.
                        has_common_part = any(
                            p in self.COMMON_NAMES or p in self.COMMON_SURNAMES 
                            for p in parts
                        )
                        
                        # Exceção: Se tiver "Dr." ou "Sra." antes, a gente confia mais
                        has_honorific = re.search(r'(?i)\b(?:dr|dra|sr|sra)\.?\s', text[max(0, ent.start_char-5):ent.start_char])

                        # Se não tem nome comum E não tem título (Dr/Sr), desconfie.
                        if not has_common_part and not has_honorific:
                            continue

                        # Se passou na validação
                        match_range = set(range(ent.start_char, ent.end_char))
                        if not match_range.intersection(indices_to_mask):
                            indices_to_mask.update(match_range)
                            pii_stats['PERSON_NAME'] += 1
                                
            except Exception:
                pass

        # 5. Anonimização
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