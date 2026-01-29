"""
Processador Standalone de PII - V20.0 (PLATINUM EDITION)
Correções Cirúrgicas:
1. NOMES: Blacklist expandida para órgãos (Sociedade, Museu, Coordenação).
2. ENDEREÇOS: 
   - Ignora 'Setor' se seguido de siglas administrativas (NUDE, SEI, GAB).
   - Lógica de MESCLAGEM: 'Área Delta' + 'Lt 105' agora contam como 1 único endereço.
3. TELEFONE: 
   - Regex de Processo atualizado para o formato exato '0315-000009878/2023-15'.
   - Verificação de borda: Telefone não pode ter '/' ou '-' antes ou depois.
4. DEDUPLICAÇÃO INTELIGENTE: PIIs adjacentes são fundidos na contagem.
"""
import pandas as pd
import spacy
import re
import os
import time
import phonenumbers
from collections import defaultdict
from typing import Dict, Tuple, List
from datetime import datetime
import sys

if sys.platform == "win32":
    os.system("")

# --- Configuração ---
FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
TARGET_COLUMN = 'Texto Mascarado'


class PIIDetector:
    """Detector de PII V20.0 - Platinum Logic"""
    
    PII_TYPES = {
        'PERSON_NAME': 'Nome de Pessoa',
        'CPF': 'Cadastro de Pessoa Física',
        'RG': 'Registro Geral (RG)',
        'CNH': 'Carteira Nacional de Habilitação',
        'MATRICULA': 'Matrícula Funcional',
        'INSCRICAO': 'Inscrição (IPTU/Municipal)',
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Número de Telefone',
        'FULL_ADDRESS': 'Endereço Completo',
        'CEP': 'Código de Endereçamento Postal',
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'LEGAL_PROCESS': 'Número de Processo', 
        'PROTOCOL': 'Número de Protocolo',     
        'SENSITIVE_HEALTH': 'Dados de Saúde (Sensível)',
        'SENSITIVE_MINOR': 'Dados de Menor de Idade (Sensível)',
        'SENSITIVE_SOCIAL': 'Dados Sociais (Sensível)',
        'SENSITIVE_RACE': 'Dados de Raça/Cor (Sensível)',
        'SENSITIVE_GENDER': 'Dados de Gênero (Sensível)'
    }

    # Blacklist Agressiva (Resolve Caso 19 e 54)
    NAME_BLACKLIST = {
        'secretaria', 'secretario', 'departamento', 'gerencia', 'ministerio', 'tribunal', 
        'vara', 'promotoria', 'defensoria', 'conselho', 'associacao', 'sindicato', 'instituto',
        'der', 'der-df', 'pmdf', 'cbmdf', 'ssp', 'sedf', 'ses', 'terracap', 'novacap',
        'caesb', 'neoenergia', 'detran', 'inss', 'receita', 'federal', 'distrito', 'procon',
        'gestor', 'ppgg', 'empresa', 'ltda', 'sa', 's/a', 'me', 'epp', 'inc', 'group',
        'consórcio', 'fundação', 'banco', 'caixa', 'hospital', 'clinica', 'universidade',
        'escola', 'faculdade', 'colegio', 'sistema', 'serviço', 'programa', 'projeto',
        'termo', 'acordo', 'cooperação', 'edital', 'concurso', 'curso', 'mestrado', 'doutorado',
        'cj', 'saúde', 'imobiliária', 'atividade', 'defesa', 'consumidor', 'fiscal',
        'venda', 'imóvel', 'monitoramento', 'ocorrência', 'carta', 'precatória',
        'sociedade', 'transportes', 'coletivos', 'museu', 'coordenação', 'pessoas', 'tcb',
        'estratégias', 'consolidação', 'melhoria', 'arquivologista', 'bolsista', 'prezados'
    }

    # Blacklist de Endereços (Resolve Caso 81 e 22)
    ADDRESS_BLACKLIST = {
        'tic', 'tecnologia', 'pessoal', 'recursos', 'humanos', 'financeiro', 'contas',
        'governanca', 'dados', 'sistemas', 'infraestrutura', 'banco', 'delta', 'administrativa',
        'nude', 'sei', 'gab', 'protocolo', 'juridico'
    }

    COMMON_SURNAMES = {
        'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira', 'alves', 'pereira', 'lima', 'gomes', 'costa', 'ribeiro', 'martins', 'carvalho', 'almeida', 'lopes', 'soares', 'fernandes', 'vieira', 'barbosa', 'rocha', 'dias', 'nascimento', 'andrade', 'moreira', 'nunes', 'marques', 'machado', 'mendes', 'freitas', 'cardoso', 'ramos', 'goncalves', 'santana', 'teixeira', 'cavalcanti', 'moura', 'campos', 'jesus', 'pinto', 'araujo', 'leite', 'barros', 'farias', 'cunha', 'reis', 'siqueira', 'moraes', 'castro', 'batista', 'neves', 'rosa', 'medeiros', 'dantas', 'conceicao', 'braga', 'filho', 'neto', 'junior', 'sobrinho', 'mota', 'vasconcelos', 'cruz', 'viana', 'peixoto', 'maia', 'monteiro', 'coelho', 'correia', 'brito', 'tavares', 'xavier', 'franco', 'maciel', 'sales', 'vasconcelos', 'cruz', 'dias', 'guimarães', 'neves', 'garcia', 'valle', 'simoes', 'barbosa', 'camargo', 'ribeiro', 'lopes'
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

        self.regex_patterns = {
            # --- BLINDAGEM ---
            # Atualizado para pegar o caso 28 e 34: 0315-000009878/2023-15 e 02305-85265475/2023-55
            'LEGAL_PROCESS': r'\b\d{4,5}[-.]\d{8,10}[/.]\d{4}[-.]\d{2}\b|\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b|\b\d{20}\b',
            'PROTOCOL': r'\b(?:LAI|PROTOCOLO|OUVIDORIA|SEI|INSCRI[ÇC][ÃA]O IMOBILI[ÁA]RIA|EMPENHO)[-:\s.]+\d{1,15}[-./]?\d{0,10}[-./]?\d{0,4}\b',
            'PROPERTY_REG': r'(?i)(?:inscri[çc][ãa]o imobili[áa]ria|im[óo]vel|matr[íi]cula do im[óo]vel)[\snº\.:]+(\d+)',

            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'CEP': r'\b\d{5}\s*[-]\s*\d{3}\b', 
            
            # Endereço: Lookahead negativo para 'Setor NUDE', 'Area Delta' (se for admin)
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|SRES|SHDF|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.|Arts|Al\.|Alameda|(?:Setor|Área)(?!\s+(?:de\s+)?(?:TIC|Tecnologia|Saúde|Pessoal|Gestão|Governança|NUDE|DER|GAB|Protocolo)))\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            
            'MATRICULA': r'(?i)\b(?:Matr[íi]cula|Siape)(?!\s+do im[óo]vel)[:\s\.]+(\w{1,15}[-.\s]?\w{0,2})\b',
            'INSCRICAO': r'(?i)\b(?:Inscri[çc][ãa]o)(?!\s+imobili[áa]ria)[:\s\.]+(\d{1,15}[-.\s]?\d{0,2})\b',
            'RG': r'(?i)(?:RG|R\.G\.|Identidade)[:\s\.]+(\d{1,2}\.?\d{3}\.?\d{3}[-.\s]?[\dX])\b',
            'CNH': r'(?i)(?:CNH|Habilita[çc][ãa]o)[:\s\.]+(\d{9,11})\b',
        }

        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [
                r'\bdiagn[oó]stico d[eo]\b', r'\bportador d[eo] (?:c[âa]ncer|hiv|aids|defici[êe]ncia)\b',
                r'\bminha doen[çc]a\b', r'\blaudo m[ée]dico\b', r'\bCID\s?[A-Z]\d', 
                r'\btranstorno (?:mental|bipolar|ansiedade)\b', r'\bexame d[eo] (?:sangue|dna|bi[óo]psia)\b',
                r'\bsofria de\b', r'\bpaciente com\b', r'\basm[áa]tic[oa]\b'
            ],
            'SENSITIVE_MINOR': [r'\bmenor de idade\b', r'\btutela d[eo] menor\b', r'\bguarda d[oa] crian[çc]a\b', r'\bfilh[oa] menor\b', r'\bcertid[ãa]o de nascimento\b', r'\bconselho tutelar\b', r'\balun[ao]\b'],
            'SENSITIVE_SOCIAL': [r'\bvulnerabilidade social\b', r'\bbenefici[áa]rio do (?:bolsa|aux[íi]lio)\b', r'\brecebe cesta b[áa]sica\b'],
            'SENSITIVE_RACE': [r'\bautodeclara[çc][ãa]o de cor\b', r'\bcor d[ae] pele\b', r'\bquesito raça\b'],
            'SENSITIVE_GENDER': [r'\bnome social\b', r'\bcirurgia de redesigna[çc][ãa]o\b', r'\bidentidade de g[êe]nero\b']
        }

    def _validate_cpf_digit(self, cpf: str) -> bool:
        if len(cpf) != 11 or not cpf.isdigit(): return False
        if cpf == cpf[0] * 11: return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf[9]): return False
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
            if any(pos in detected_positions for pos in range(match.start(), match.end())): continue
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
        protected_indices = set()
        pii_stats = defaultdict(int)
        invalid_cpfs = defaultdict(int)
        
        # Estrutura para mesclagem: lista de (start, end, type)
        detected_items = [] 
        
        has_identifier = False

        # --- 1. BLINDAGEM ---
        for blind_type in ['LEGAL_PROCESS', 'PROTOCOL', 'PROPERTY_REG']:
            for match in re.finditer(self.regex_patterns[blind_type], text):
                protected_indices.update(range(match.start(), match.end()))
                
        # --- 2. CPF ---
        for start, end, is_valid in self._detect_cpf(text):
            if not protected_indices.intersection(range(start, end)):
                indices_to_mask.update(range(start, end))
                detected_items.append((start, end, 'CPF'))
                has_identifier = True
                if not is_valid:
                    invalid_cpfs['CPF_INVALID'] += 1

        # --- 3. NOMES (Gatilhos + IA + Regex) ---
        detected_names_ranges = set()
        
        # 3.1 Gatilhos
        trigger_pattern = r'(?i)(?:Nome|Representante|Pai|Mãe|Orientador|Professor|Prof\.|Dr\.|Dra\.|Contat(?:o|ar)|Sr\.|Sra\.|Servidor|Alun[ao])[:\s]+((?:[A-Z][a-zÀ-ÿ]+\s*){2,})'
        for match in re.finditer(trigger_pattern, text):
            start_name, end_name = match.span(1)
            name_text = match.group(1).strip().lower()
            if any(b in name_text for b in self.NAME_BLACKLIST): continue
            
            if not protected_indices.intersection(range(start_name, end_name)):
                if not set(range(start_name, end_name)).intersection(indices_to_mask):
                    indices_to_mask.update(range(start_name, end_name))
                    detected_names_ranges.update(range(start_name, end_name))
                    detected_items.append((start_name, end_name, 'PERSON_NAME'))
                    has_identifier = True

        # 3.2 SpaCy
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        if not protected_indices.intersection(range(ent.start_char, ent.end_char)):
                            if not set(range(ent.start_char, ent.end_char)).intersection(detected_names_ranges):
                                name_text = ent.text.strip().lower()
                                if any(b in name_text for b in self.NAME_BLACKLIST): continue
                                if ent.text.isupper() and len(ent.text) < 10: continue
                                clean_name = re.sub(r'[^\w\s]', '', name_text)
                                parts = clean_name.split()
                                if len(parts) < 2: continue
                                if "ltda" in clean_name or "advogados" in clean_name: continue
                                has_common = any(p in self.COMMON_SURNAMES for p in parts)
                                has_honor = re.search(r'(?i)\b(?:dr|dra|sr|sra)\.?\s', text[max(0, ent.start_char-5):ent.start_char])
                                if has_common or has_honor:
                                    indices_to_mask.update(range(ent.start_char, ent.end_char))
                                    detected_names_ranges.update(range(ent.start_char, ent.end_char))
                                    detected_items.append((ent.start_char, ent.end_char, 'PERSON_NAME'))
                                    has_identifier = True
            except Exception:
                pass

        # 3.3 Regex Fallback
        fallback_name_pattern = r'\b([A-Z][a-zçáéíóúãõâêô]+(?:\s(?:da|de|do|dos|das|e)\s)?(?:[A-Z][a-zçáéíóúãõâêô]+)+)\b'
        for match in re.finditer(fallback_name_pattern, text):
            start, end = match.span()
            name_text = match.group(1).lower()
            if set(range(start, end)).intersection(detected_names_ranges): continue
            if any(b in name_text for b in self.NAME_BLACKLIST): continue
            parts = name_text.split()
            if any(p in self.COMMON_SURNAMES for p in parts):
                if not protected_indices.intersection(range(start, end)):
                    indices_to_mask.update(range(start, end))
                    detected_items.append((start, end, 'PERSON_NAME'))
                    has_identifier = True

        # --- 4. DOCUMENTOS ---
        for doc_type in ['MATRICULA', 'INSCRICAO', 'RG', 'CNH', 'CNPJ', 'CEP']:
            if doc_type in self.regex_patterns:
                for match in re.finditer(self.regex_patterns[doc_type], text):
                    if match.groups():
                        start, end = match.span(1)
                    else:
                        start, end = match.span()
                    
                    if not protected_indices.intersection(range(start, end)):
                        if not set(range(start, end)).intersection(indices_to_mask):
                            indices_to_mask.update(range(start, end))
                            detected_items.append((start, end, doc_type))
                            if doc_type in ['RG', 'CNH', 'MATRICULA']:
                                has_identifier = True

        # --- 5. ENDEREÇO E EMAIL ---
        for pii_type in ['EMAIL', 'FULL_ADDRESS']:
            for match in re.finditer(self.regex_patterns[pii_type], text):
                start, end = match.span()
                content = match.group().lower()
                if pii_type == 'FULL_ADDRESS':
                    if any(bad in content for bad in self.ADDRESS_BLACKLIST): continue
                if not protected_indices.intersection(range(start, end)):
                    if not set(range(start, end)).intersection(indices_to_mask):
                        indices_to_mask.update(range(start, end))
                        detected_items.append((start, end, pii_type))

        # --- 6. TELEFONE ---
        phone_patterns = [
            r'\b(?:\(?\s*(?:1[1-9]|2[1-247-8]|3[1-57-8]|4[1-9]|5[13-5]|6[1-9]|7[13-579]|8[1-9]|9[1-9])\s*\)?\s?)?(?:9\s?\d{4}[-.\s]?\d{4}|\d{4}[-.\s]?\d{4})\b',
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,15}\b'
        ]
        
        for pattern in phone_patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                match_range = set(range(start, end))
                if re.search(r'(?:19|20)\d{2}$', match.group().strip()): continue 
                
                # Check arredores (evita pegar parte de processo)
                prefix = text[max(0, start-1):start]
                suffix = text[end:min(len(text), end+1)]
                if prefix in ['/', '-'] or suffix in ['/', '-']: continue

                if protected_indices.intersection(match_range): continue
                if match_range.intersection(indices_to_mask): continue
                
                indices_to_mask.update(match_range)
                detected_items.append((start, end, 'PHONE'))

        # --- 7. DADOS SENSÍVEIS ---
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    if has_identifier:
                        match_range = set(range(match.start(), match.end()))
                        if not protected_indices.intersection(match_range):
                            indices_to_mask.update(match_range)
                            detected_items.append((match.start(), match.end(), sens_type))

        # --- PROCESSAMENTO ESTATÍSTICO (MESCLAGEM) ---
        # Aqui corrigimos o problema de contar "Área Delta" e "Lt 105" como 2
        detected_items.sort(key=lambda x: x[0])
        merged_stats = defaultdict(int)
        
        if detected_items:
            current_start, current_end, current_type = detected_items[0]
            
            for i in range(1, len(detected_items)):
                next_start, next_end, next_type = detected_items[i]
                
                # Se forem do mesmo tipo e estiverem perto (ex: endereço quebrado)
                if next_type == current_type and (next_start - current_end) < 5:
                    # Mescla
                    current_end = max(current_end, next_end)
                else:
                    # Salva anterior e inicia novo
                    merged_stats[current_type] += 1
                    current_start, current_end, current_type = next_start, next_end, next_type
            
            merged_stats[current_type] += 1 # Salva o último

        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask:
                redacted_chars.append('x' if char.isalnum() else char)
            else:
                redacted_chars.append(char)
        
        return "".join(redacted_chars), dict(merged_stats), dict(invalid_cpfs)

    def get_description(self, key: str) -> str:
        return self.PII_TYPES.get(key, key)


class Logger:
    """Sistema de logging"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GREY = '\033[90m'
    BG_RED = '\033[101m'
    BG_YELLOW = '\033[103m'
    BG_GREEN = '\033[102m'
    
    @staticmethod
    def header(message: str):
        print(f"\n{'=' * 80}")
        print(f"{Logger.BOLD}{Logger.CYAN}  {message}{Logger.RESET}")
        print(f"{'=' * 80}\n")
    
    @staticmethod
    def section(title: str):
        print(f"\n{Logger.BOLD}{Logger.WHITE}{title}{Logger.RESET}")
        print(f"{Logger.DIM}{'─' * 80}{Logger.RESET}")
    
    @staticmethod
    def metric(label: str, value: str, alert: bool = False):
        if alert:
            symbol = f"{Logger.RED}▲{Logger.RESET}"
            value_colored = f"{Logger.RED}{Logger.BOLD}{value}{Logger.RESET}"
        else:
            symbol = " "
            value_colored = f"{Logger.GREEN}{value}{Logger.RESET}"
        print(f"  {symbol} {label:<38} {value_colored:>20}")
    
    @staticmethod
    def category(name: str, count: int, is_sensitive: bool = False):
        if is_sensitive:
            badge = f"{Logger.BG_RED}{Logger.WHITE} CRÍTICO {Logger.RESET}"
            bullet = f"{Logger.RED}●{Logger.RESET}"
        else:
            badge = f"{Logger.BG_YELLOW}{Logger.WHITE} ALERTA {Logger.RESET}"
            bullet = f"{Logger.YELLOW}●{Logger.RESET}"
        print(f"  {bullet} {badge} {Logger.BOLD}{name}{Logger.RESET} {Logger.DIM}({count} ocorrências){Logger.RESET}")
    
    @staticmethod
    def records(records_str: str):
        print(f"    {Logger.GREY}└─ Registros: {records_str}{Logger.RESET}")
    
    @staticmethod
    def alert_box(message: str, level: str = "CRÍTICO"):
        if level == "CRÍTICO":
            color = Logger.RED
            bg = Logger.BG_RED
        elif level == "ALTO":
            color = Logger.YELLOW
            bg = Logger.BG_YELLOW
        else:
            color = Logger.GREEN
            bg = Logger.BG_GREEN
        print(f"\n{'=' * 80}")
        print(f"{bg}{Logger.WHITE}{Logger.BOLD}  ⚠  CLASSIFICAÇÃO: PEDIDO NÃO PÚBLICO ({level})  {Logger.RESET}")
        print(f"{color}  {message}{Logger.RESET}")
        print(f"{'=' * 80}\n")
    
    @staticmethod
    def info(message: str, indent: int = 2):
        print(f"{' ' * indent}{Logger.GREY}{message}{Logger.RESET}")
    
    @staticmethod
    def success(message: str):
        print(f"  {Logger.GREEN}✓{Logger.RESET} {message}")
    
    @staticmethod
    def warning(message: str):
        print(f"  {Logger.YELLOW}⚠{Logger.RESET} {Logger.BOLD}{message}{Logger.RESET}")
    
    @staticmethod
    def recommendation(message: str, is_critical: bool = False):
        symbol = f"{Logger.RED}✗{Logger.RESET}" if is_critical else f"{Logger.YELLOW}⚠{Logger.RESET}"
        print(f"  {symbol} {message}")


def generate_report(df: pd.DataFrame, pii_details: dict, records_with_pii: int, 
                   processing_time: float, detector: PIIDetector, filename: str,
                   invalid_cpf_count: int, record_risk_analysis: dict):
    
    logger = Logger()
    total_records = len(df)
    
    # --- PRÉ-PROCESSAMENTO DAS LISTAS ---
    public_records = []
    moderate_records = []
    critical_records = []
    
    for record_id, risk_info in record_risk_analysis.items():
        if risk_info['level'] == 'PÚBLICO':
            public_records.append(record_id)
        elif risk_info['level'] == 'MODERADO':
            moderate_records.append(record_id)
        else:
            critical_records.append(record_id)

    non_public_records = sorted(moderate_records + critical_records, key=lambda x: int(x) if str(x).isdigit() else str(x))

    # === CABEÇALHO DO RELATÓRIO ===
    logger.header(f"ANÁLISE DE PEDIDOS - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info(f"Arquivo: {os.path.basename(filename)}", indent=0)
    logger.info(f"Processador: PII Detector v20.0 (Platinum Edition)", indent=0)
    
    logger.section("INDICADORES DE PROCESSAMENTO")
    pii_rate = (records_with_pii / total_records * 100) if total_records > 0 else 0
    logger.metric("Total de registros analisados", f"{total_records:,}")
    logger.metric("Registros com dados pessoais", f"{records_with_pii:,}", alert=records_with_pii > 0)
    logger.metric("Registros sem dados pessoais", f"{total_records - records_with_pii:,}")
    logger.metric("Taxa de incidência", f"{pii_rate:.2f}%", alert=pii_rate > 10)
    logger.metric("Tempo de processamento", f"{processing_time:.2f}s")

    print(f"\n{'=' * 80}\n")
    # === 1. RESULTADO PRINCIPAL ===
    print(f"\n{Logger.BOLD}{Logger.WHITE}RESULTADO PRINCIPAL{Logger.RESET}")
    print(f"{Logger.DIM}{'─' * 80}{Logger.RESET}")

    # PEDIDOS PÚBLICOS
    print(f"\n{Logger.GREEN}PEDIDOS PÚBLICOS{Logger.RESET}")
    print(f"  (Podem ser divulgados - Sem informações pessoais)")
    print(f"  Total: {len(public_records)}")
    if public_records:
        ids_str = ', '.join([str(rid) for rid in public_records])
        print(f"  {Logger.GREY}IDs: {ids_str}{Logger.RESET}")
    
    # PEDIDOS NÃO PÚBLICOS
    print(f"\n{Logger.RED}PEDIDOS NÃO PÚBLICOS (Informações Pessoais){Logger.RESET}")
    print(f"  (Todos os pedidos que contenham informações pessoais)")
    print(f"  Total: {len(non_public_records)}")
    if non_public_records:
        ids_str = ', '.join([str(rid) for rid in non_public_records])
        print(f"  {Logger.GREY}IDs: {ids_str}{Logger.RESET}")
        
    print(f"\n{'=' * 80}\n")
    
    # === 3. CLASSIFICAÇÃO INDIVIDUAL ===
    logger.section("CLASSIFICAÇÃO INDIVIDUAL DOS REGISTROS")
    
    if public_records:
        logger.info(f"{Logger.GREEN}✓ REGISTROS PÚBLICOS{Logger.RESET} (podem ser divulgados)", indent=2)
        logger.info(f"Total: {len(public_records)}", indent=4)
        logger.info(f"IDs: {', '.join([str(rid) for rid in public_records])}", indent=4)
        print()
    
    if moderate_records:
        logger.info(f"{Logger.YELLOW}⚠ REGISTROS COM RISCO MODERADO{Logger.RESET} (requerem revisão)", indent=2)
        logger.info(f"Total: {len(moderate_records)}", indent=4)
        logger.info(f"Contêm: e-mail, telefone, endereço, CNPJ, Inscrição", indent=4)
        logger.info(f"IDs: {', '.join([str(rid) for rid in moderate_records])}", indent=4)
        print()
    
    if critical_records:
        logger.info(f"{Logger.RED}✗ REGISTROS CRÍTICOS{Logger.RESET} (NÃO divulgar)", indent=2)
        logger.info(f"Total: {len(critical_records)}", indent=4)
        logger.info(f"Contêm: CPF, RG, CNH, Matrícula, Dados Sensíveis", indent=4)
        logger.info(f"IDs: {', '.join([str(rid) for rid in critical_records])}", indent=4)
        print()
        logger.info(f"{Logger.DIM}Detalhamento COMPLETO dos registros críticos:{Logger.RESET}", indent=4)
        for record_id in critical_records: 
            reasons = record_risk_analysis[record_id]['reasons']
            logger.info(f"  #{record_id}: {', '.join(reasons)}", indent=4)
    
    if pii_details:
        logger.section("DETALHAMENTO POR CATEGORIA DE DADOS")
        sorted_details = sorted(pii_details.items(), key=lambda x: sum(i['qtd'] for i in x[1]), reverse=True)
        for pii_type, occurrences in sorted_details:
            total_count = sum(item['qtd'] for item in occurrences)
            desc = detector.get_description(pii_type)
            critical_types = ['CPF', 'RG', 'CNH', 'MATRICULA', 'SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_RACE', 'SENSITIVE_GENDER', 'SENSITIVE_SOCIAL']
            is_sensitive = pii_type in critical_types
            
            records_list = [f"#{item['id']} ({item['qtd']}x)" for item in occurrences]
            logger.category(desc, total_count, is_sensitive)
            logger.records(", ".join(records_list))
    else:
        logger.section("DETALHAMENTO POR CATEGORIA DE DADOS")
        logger.info("Nenhum dado pessoal identificado", indent=2)
    
    if invalid_cpf_count > 0:
        logger.section("ALERTAS DE QUALIDADE")
        logger.warning(f"Detectados {invalid_cpf_count} CPF(s) com formato inválido")
    
    print(f"\n{'=' * 80}\n")


def main():
    if not os.path.exists(FILE_NAME):
        print(f"✗ Erro: Arquivo '{FILE_NAME}' não encontrado.")
        return
    
    print("Iniciando Análise de Pedidos...")
    detector = PIIDetector()
    
    try:
        df = pd.read_csv(FILE_NAME) if FILE_NAME.endswith('.csv') else pd.read_excel(FILE_NAME)
        print(f"✓ Arquivo carregado: {len(df)} registros")
    except Exception as e:
        print(f"✗ Erro ao ler arquivo: {e}")
        return

    df.columns = [c.strip() for c in df.columns]
    target_col = next((c for c in df.columns if TARGET_COLUMN.lower() in c.lower()), None)
    if not target_col:
        for col in df.columns:
            if df[col].dtype == 'object' and df[col].str.len().mean() > 20:
                target_col = col
                break
    if not target_col:
        print("✗ Erro: Coluna de texto não identificada.")
        return

    possible_id_cols = ['id', 'ID', 'Id', 'Protocolo', 'protocolo']
    id_col = next((col for col in possible_id_cols if col in df.columns), None)

    print(f"Processando coluna '{target_col}'...", end=' ', flush=True)
    start_time = time.time()
    
    pii_details = defaultdict(list)
    records_with_pii = 0
    total_invalid_cpfs = 0
    record_risk_analysis = {}
    
    critical_categories = {'CPF', 'RG', 'CNH', 'MATRICULA', 
                          'SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 
                          'SENSITIVE_RACE', 'SENSITIVE_GENDER'}
    
    moderate_categories = {'EMAIL', 'PHONE', 'FULL_ADDRESS', 'PERSON_NAME', 'CNPJ', 'INSCRICAO', 'CEP'}

    for idx, row in df.iterrows():
        text_content = str(row[target_col])
        _, stats, invalid_stats = detector.detect_and_redact(text_content)
        
        record_id = row[id_col] if id_col else f"Linha_{idx + 2}"
        
        if stats:
            records_with_pii += 1
            has_critical = any(cat in stats for cat in critical_categories)
            has_moderate = any(cat in stats for cat in moderate_categories)
            
            if has_critical:
                critical_found = [detector.get_description(cat) for cat in stats.keys() if cat in critical_categories]
                record_risk_analysis[record_id] = {'level': 'CRÍTICO', 'reasons': critical_found}
            elif has_moderate:
                moderate_found = [detector.get_description(cat) for cat in stats.keys() if cat in moderate_categories]
                record_risk_analysis[record_id] = {'level': 'MODERADO', 'reasons': moderate_found}
            
            for pii_type, count in stats.items():
                pii_details[pii_type].append({'id': record_id, 'qtd': count})
            if 'CPF_INVALID' in invalid_stats:
                total_invalid_cpfs += invalid_stats['CPF_INVALID']
        else:
            record_risk_analysis[record_id] = {'level': 'PÚBLICO', 'reasons': []}
    
    processing_time = time.time() - start_time
    print("Concluído ✓")

    generate_report(df, pii_details, records_with_pii, processing_time, detector, 
                   FILE_NAME, total_invalid_cpfs, record_risk_analysis)

if __name__ == "__main__":
    main()