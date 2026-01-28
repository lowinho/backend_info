import spacy
import re
import phonenumbers
import pandas as pd
from collections import defaultdict
from typing import Tuple, Dict, List

class PIIDetector:
    """
    Detector de PII V13.0 (Context Aware) - Backend Service
    Sincronizado com o script de terminal.
    """
    
    PII_TYPES = {
        'PERSON_NAME': 'Nome de Pessoa',
        'CPF': 'Cadastro de Pessoa Física',
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Número de Telefone',
        'FULL_ADDRESS': 'Endereço Completo',
        'CEP': 'Código de Endereçamento Postal',
        'GENERAL_REGISTRY': 'Registros Gerais (RG/NIS/PIS/CNH)',
        'SENSITIVE_HEALTH': 'Dados de Saúde (Sensível)',
        'SENSITIVE_MINOR': 'Dados de Menor de Idade (Sensível)',
        'SENSITIVE_SOCIAL': 'Dados Sociais (Sensível)',
        'SENSITIVE_RACE': 'Dados de Raça/Cor (Sensível)',
        'SENSITIVE_GENDER': 'Dados de Gênero (Sensível)'
    }

    # Base de conhecimento para validação de nomes (IBGE)
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

    CPF_CONTEXT_KEYWORDS = [
        r'cpf', r'cadastro de pessoa f[íi]sica', r'inscri[çc][ãa]o', 
        r'inscrito no cpf', r'cpf n[úu]mero', r'cpf sob o n[úu]mero',
        r'portador do cpf', r'titular do cpf', r'contribuinte',
        r'documento cpf', r'cadastro cpf'
    ]

    def __init__(self):
        try:
            self.nlp = spacy.load("pt_core_news_lg")
            pipes_to_disable = ['parser', 'tagger', 'morphologizer', 'lemmatizer']
            existing_pipes = [p for p in pipes_to_disable if p in self.nlp.pipe_names]
            if existing_pipes:
                self.nlp.disable_pipes(existing_pipes)
        except OSError:
            self.nlp = None

        self.phone_patterns = [
            r'\b(?:\(?[1-9]{2}\)?\s?)(?:9\s?\d|[2-5]\d)\d{2}[-.\s]\d{4}\b',
            r'\b[1-9]{2}9\d{8}\b',
            r'\b[1-9]{2}[2-5]\d{7}\b',
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,12}\b'
        ]

        self.regex_patterns = {
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'CEP': r'\b\d{5}\s*[-]\s*\d{3}\b', 
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|SRES|SHDF|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.|Arts|Al\.|Alameda)\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            'GENERAL_REGISTRY': r'(?i)(?:RG|CNH|Matr[íi]cula|NIS|PIS|PASEP|NIT|CTPS|IPTU|Inscri[çc][ãa]o|T[íi]tulo\s(?:de\s)?Eleitor)(?!\s*cpf)[:\s\.]+\d{1,15}[-\d]*|\b\d{3}\.\d{5}\.\d{2}-\d\b'
        }

        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [
                r'\bdiagn[oó]stico d[eo]\b', 
                r'\bportador d[eo] (?:c[âa]ncer|hiv|aids|defici[êe]ncia)\b',
                r'\bminha doen[çc]a\b', 
                r'\blaudo m[ée]dico\b', 
                r'\bCID\s?[A-Z]\d', 
                r'\btranstorno (?:mental|bipolar|ansiedade)\b',
                r'\bexame d[eo] (?:sangue|dna|bi[óo]psia)\b',
                r'\bsofria de\b',
                r'\bpaciente com\b'
            ],
            'SENSITIVE_MINOR': [
                r'\bmenor de idade\b', 
                r'\btutela d[eo] menor\b', 
                r'\bguarda d[oa] crian[çc]a\b',
                r'\bfilh[oa] menor\b',
                r'\badolescente infrator\b',
                r'\bcertid[ãa]o de nascimento\b',
                r'\bconselho tutelar\b'
            ],
            'SENSITIVE_SOCIAL': [
                r'\bvulnerabilidade social\b', 
                r'\bbenefici[áa]rio do (?:bolsa|aux[íi]lio)\b', 
                r'\brecebe cesta b[áa]sica\b', 
                r'\bcad[úu]nico\b'
            ],
            'SENSITIVE_RACE': [
                r'\bautodeclara[çc][ãa]o de cor\b', 
                r'\bcor d[ae] pele\b', 
                r'\bquesito raça\b'
            ],
            'SENSITIVE_GENDER': [
                r'\bnome social\b', 
                r'\bcirurgia de redesigna[çc][ãa]o\b', 
                r'\bidentidade de g[êe]nero\b'
            ]
        }

    def _validate_cpf_digit(self, cpf: str) -> bool:
        if len(cpf) != 11 or not cpf.isdigit():
            return False
        if cpf == cpf[0] * 11:
            return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf[9]):
            return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        return digito2 == int(cpf[10])

    def _has_cpf_context(self, text: str, position: int, window: int = 50) -> bool:
        start = max(0, position - window)
        end = min(len(text), position + window)
        context = text[start:end].lower()
        return any(re.search(keyword, context, re.IGNORECASE) for keyword in self.CPF_CONTEXT_KEYWORDS)

    def _detect_cpf(self, text: str) -> List[Tuple[int, int, bool]]:
        cpf_matches = []
        detected_positions = set()
        formatted_pattern = r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'
        for match in re.finditer(formatted_pattern, text):
            cpf_digits = re.sub(r'\D', '', match.group())
            is_valid = self._validate_cpf_digit(cpf_digits)
            cpf_matches.append((match.start(), match.end(), is_valid))
            detected_positions.update(range(match.start(), match.end()))
        loose_pattern = r'\b\d{11}\b'
        for match in re.finditer(loose_pattern, text):
            if any(pos in detected_positions for pos in range(match.start(), match.end())):
                continue
            if self._has_cpf_context(text, match.start()):
                cpf_candidate = match.group()
                is_valid = self._validate_cpf_digit(cpf_candidate)
                cpf_matches.append((match.start(), match.end(), is_valid))
                detected_positions.update(range(match.start(), match.end()))
        return cpf_matches

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int], Dict[str, int]]:
        if pd.isna(text) or not isinstance(text, str):
            return text, {}, {}
        
        indices_to_mask = set()
        pii_stats = defaultdict(int)
        invalid_cpfs = defaultdict(int)
        
        has_identifier = False

        # 1. CPF
        for start, end, is_valid in self._detect_cpf(text):
            indices_to_mask.update(range(start, end))
            pii_stats['CPF'] += 1
            has_identifier = True
            if not is_valid:
                invalid_cpfs['CPF_INVALID'] += 1
        
        # 2. Nomes (NLP)
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        name_candidate = ent.text.strip()
                        clean_name = re.sub(r'[^\w\s]', '', name_candidate.lower())
                        parts = clean_name.split()
                        if len(parts) < 2: continue
                        
                        has_common = any(p in self.COMMON_NAMES or p in self.COMMON_SURNAMES for p in parts)
                        has_honor = re.search(r'(?i)\b(?:dr|dra|sr|sra)\.?\s', text[max(0, ent.start_char-5):ent.start_char])

                        if has_common or has_honor:
                            match_range = set(range(ent.start_char, ent.end_char))
                            if not match_range.intersection(indices_to_mask):
                                indices_to_mask.update(match_range)
                                pii_stats['PERSON_NAME'] += 1
                                has_identifier = True
            except Exception:
                pass

        # 3. Registros Gerais (RG, etc)
        for match in re.finditer(self.regex_patterns['GENERAL_REGISTRY'], text):
            match_range = set(range(match.start(), match.end()))
            if not match_range.intersection(indices_to_mask):
                indices_to_mask.update(match_range)
                pii_stats['GENERAL_REGISTRY'] += 1
                has_identifier = True

        # CNPJ
        for match in re.finditer(self.regex_patterns['CNPJ'], text):
            match_range = set(range(match.start(), match.end()))
            if not match_range.intersection(indices_to_mask):
                indices_to_mask.update(match_range)
                pii_stats['CNPJ'] += 1

        # Email / Endereço / Telefone / CEP
        for pii_type in ['EMAIL', 'FULL_ADDRESS', 'CEP']:
            if pii_type in self.regex_patterns:
                for match in re.finditer(self.regex_patterns[pii_type], text):
                    match_range = set(range(match.start(), match.end()))
                    if not match_range.intersection(indices_to_mask):
                        indices_to_mask.update(match_range)
                        stats_key = 'FULL_ADDRESS' if pii_type == 'CEP' else pii_type
                        pii_stats[stats_key] += 1

        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text):
                match_range = set(range(match.start(), match.end()))
                if not match_range.intersection(indices_to_mask):
                    indices_to_mask.update(match_range)
                    pii_stats['PHONE'] += 1

        try:
            for match in phonenumbers.PhoneNumberMatcher(text, "BR"):
                if phonenumbers.is_valid_number(match.number):
                    match_range = set(range(match.start, match.end))
                    if not match_range.intersection(indices_to_mask):
                        indices_to_mask.update(match_range)
                        pii_stats['PHONE'] += 1
        except Exception:
            pass

        # Contextual Sensitive Data
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    if has_identifier:
                        indices_to_mask.update(range(match.start(), match.end()))
                        pii_stats[sens_type] += 1

        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask:
                redacted_chars.append('x' if char.isalnum() else char)
            else:
                redacted_chars.append(char)
        
        return "".join(redacted_chars), dict(pii_stats), dict(invalid_cpfs)

    def get_description(self, key: str) -> str:
        return self.PII_TYPES.get(key, key)