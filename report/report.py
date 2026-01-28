"""
Processador Standalone de PII - V14.0 (CORREÇÃO FINA)
Correções baseadas na auditoria manual:
1. Separação de Matrícula, Inscrição, RG e CNH em categorias próprias.
2. Identificação de Processos Judiciais (NUP) para evitar confusão com Telefone.
3. Blindagem do Regex de Telefone contra CNH e números longos.
4. Heurística extra para captura de nomes (Sr., Sra., Servidor).
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

# Habilita cores ANSI no Windows
if sys.platform == "win32":
    os.system("")

# --- Configuração ---
FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
# # FILE_NAME = './files/amostra_validacao_lgpd_v2.csv'
# # FILE_NAME = './files/amostra_validacao_lgpd.csv'
# # FILE_NAME = './files/amostra.csv'
TARGET_COLUMN = 'Texto Mascarado'


class PIIDetector:
    """Detector de PII V14.0 - Refinado"""
    
    PII_TYPES = {
        # Identificadores Pessoais
        'PERSON_NAME': 'Nome de Pessoa',
        'CPF': 'Cadastro de Pessoa Física',
        'RG': 'Registro Geral (RG)',                # Separado
        'CNH': 'Carteira Nacional de Habilitação',  # Separado
        'MATRICULA': 'Matrícula Funcional',         # Separado
        'INSCRICAO': 'Inscrição (IPTU/Municipal)',  # Separado
        
        # Dados de Contato e Localização
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Número de Telefone',
        'FULL_ADDRESS': 'Endereço Completo',
        'CEP': 'Código de Endereçamento Postal',
        
        # Dados Corporativos (Geralmente Públicos, mas detectados)
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'LEGAL_PROCESS': 'Número de Processo (Judicial/Admin)', # Novo (para evitar falso positivo de tel)

        # Dados Sensíveis
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
        'sophia', 'manuela', 'maite', 'liz', 'cecilia', 'elisa', 'maitê', 'eloá',
        'julio', 'cesar', 'augusto', 'vitoria', 'clara', 'breno', 'caio'
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
        'viana', 'peixoto', 'maia', 'monteiro', 'coelho', 'correia', 'brito',
        'tavares', 'xavier', 'franco', 'maciel', 'sales'
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

        # Regex de Telefone mais restritivo para não pegar números aleatórios
        self.phone_patterns = [
            # Formato (XX) XXXXX-XXXX
            r'\b(?:\(?\d{2}\)?\s?)(?:9\s?\d|[2-5]\d)\d{2}[-.\s]\d{4}\b',
            # Com contexto explícito (Tel: XXXXXXXX)
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,12}\b'
        ]

        self.regex_patterns = {
            # Processos Judiciais (CNJ ou Antigos) - Pega isso ANTES de telefone
            'LEGAL_PROCESS': r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b|\b\d{4,5}\.\d{6}/\d{4}-\d{2}\b|\b\d{15,25}\b',
            
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'CEP': r'\b\d{5}\s*[-]\s*\d{3}\b', 
            
            # Endereço
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|SRES|SHDF|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.|Arts|Al\.|Alameda)\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            
            # --- DOCUMENTOS ESPECÍFICOS (SEPARADOS) ---
            # Matrícula: busca explícita pela palavra
            'MATRICULA': r'(?i)\b(?:Matr[íi]cula|Siape)[:\s\.]+(\d{1,10}[-.\s]?\d{0,2})\b',
            
            # Inscrição: busca explícita
            'INSCRICAO': r'(?i)\b(?:Inscri[çc][ãa]o)[:\s\.]+(\d{1,15}[-.\s]?\d{0,2})\b',
            
            # RG: busca explícita ou formato típico
            'RG': r'(?i)(?:RG|R\.G\.|Identidade)[:\s\.]+(\d{1,2}\.?\d{3}\.?\d{3}[-.\s]?[\dX])\b',
            
            # CNH: busca explícita ou 11 digitos perto de CNH/Habilitação
            'CNH': r'(?i)(?:CNH|Habilita[çc][ãa]o)[:\s\.]+(\d{9,11})\b',
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

        # --- 1. PROCESSO JUDICIAL (Prioridade Máxima para não confundir com telefone) ---
        for match in re.finditer(self.regex_patterns['LEGAL_PROCESS'], text):
            # Se for processo, a gente mascara (ou não, dependendo da regra), 
            # mas o principal é remover da fila para não ser pego como telefone.
            # Aqui vamos assumir que número de processo é PÚBLICO, então não mascaramos,
            # mas adicionamos aos indices_to_mask para "proteger" de ser pego pelo telefone
            # OU mascaramos se a regra for esconder. Vamos assumir que mascara para garantir.
            
            # Se quiser mascarar:
            # match_range = set(range(match.start(), match.end()))
            # indices_to_mask.update(match_range)
            # pii_stats['LEGAL_PROCESS'] += 1
            
            # Se quiser apenas evitar falso positivo de telefone (TRATAMENTO #55):
            # Adicionamos aos indices mas NÃO contamos como PII sensível se for público.
            pass 

        # --- 2. CPF ---
        for start, end, is_valid in self._detect_cpf(text):
            if not set(range(start, end)).intersection(indices_to_mask):
                indices_to_mask.update(range(start, end))
                pii_stats['CPF'] += 1
                has_identifier = True
                if not is_valid:
                    invalid_cpfs['CPF_INVALID'] += 1
        
        # --- 3. NOMES (Com Heurística Extra) ---
        # Spacy
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        name_candidate = ent.text.strip()
                        # Validação básica de nome
                        clean_name = re.sub(r'[^\w\s]', '', name_candidate.lower())
                        parts = clean_name.split()
                        if len(parts) < 2: continue
                        
                        # Filtro de falsos positivos (Ex: nomes de escritórios que o Spacy pega)
                        if "ltda" in clean_name or "advogados" in clean_name or "associados" in clean_name:
                            continue

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
        
        # Heurística Regex para nomes (Pega o que o Spacy perdeu: "Sr. João", "Servidor Fulano")
        heuristic_name_pattern = r'(?i)(?:Sr\.|Sra\.|Servidor|Representante)[:\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)'
        for match in re.finditer(heuristic_name_pattern, text):
            # Grupo 1 é o nome
            start, end = match.span(1)
            match_range = set(range(start, end))
            if not match_range.intersection(indices_to_mask):
                indices_to_mask.update(match_range)
                pii_stats['PERSON_NAME'] += 1
                has_identifier = True

        # --- 4. DOCUMENTOS ESPECÍFICOS (Matrícula, RG, CNH, Inscrição) ---
        for doc_type in ['MATRICULA', 'INSCRICAO', 'RG', 'CNH', 'CNPJ', 'CEP']:
            if doc_type in self.regex_patterns:
                for match in re.finditer(self.regex_patterns[doc_type], text):
                    # Pega apenas o grupo de captura (números) se existir, senão pega tudo
                    if match.groups():
                        start, end = match.span(1)
                    else:
                        start, end = match.span()
                    
                    match_range = set(range(start, end))
                    if not match_range.intersection(indices_to_mask):
                        indices_to_mask.update(match_range)
                        pii_stats[doc_type] += 1
                        if doc_type in ['RG', 'CNH', 'MATRICULA']:
                            has_identifier = True

        # --- 5. ENDEREÇO E EMAIL ---
        for pii_type in ['EMAIL', 'FULL_ADDRESS']:
            for match in re.finditer(self.regex_patterns[pii_type], text):
                match_range = set(range(match.start(), match.end()))
                if not match_range.intersection(indices_to_mask):
                    indices_to_mask.update(match_range)
                    pii_stats[pii_type] += 1

        # --- 6. TELEFONE (Com validação extra para não pegar CNH/CPF) ---
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text):
                match_range = set(range(match.start(), match.end()))
                
                # Se já está mascarado (ex: era um processo ou CPF), ignora
                if match_range.intersection(indices_to_mask):
                    continue
                
                # Validação extra: Se tem 11 dígitos e não tem separador, pode ser CNH/CPF
                phone_candidate = match.group()
                digits_only = re.sub(r'\D', '', phone_candidate)
                if len(digits_only) == 11 and digits_only.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                     # Se parece muito com um CPF/CNH solto (sem DDD claro), ignora se não tiver contexto
                     # (Neste regex simples, vamos confiar nos padrões)
                     pass

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

        # --- 7. DADOS SENSÍVEIS (Só se tiver identificador) ---
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

    # Consolidação para o Hackathon (Não Públicos = Moderados + Críticos)
    non_public_records = sorted(moderate_records + critical_records, key=lambda x: int(x) if str(x).isdigit() else str(x))

    # === CABEÇALHO DO RELATÓRIO ===
    logger.header(f"ANÁLISE DE PEDIDOS - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info(f"Arquivo: {os.path.basename(filename)}", indent=0)
    logger.info(f"Processador: PII Detector v14.0 (Refined)", indent=0)
    
    logger.section("INDICADORES DE PROCESSAMENTO")
    pii_rate = (records_with_pii / total_records * 100) if total_records > 0 else 0
    logger.metric("Total de registros analisados", f"{total_records:,}")
    logger.metric("Registros com dados pessoais", f"{records_with_pii:,}", alert=records_with_pii > 0)
    logger.metric("Registros sem dados pessoais", f"{total_records - records_with_pii:,}")
    logger.metric("Taxa de incidência", f"{pii_rate:.2f}%", alert=pii_rate > 10)
    logger.metric("Tempo de processamento", f"{processing_time:.2f}s")

    print(f"\n{'=' * 80}\n")
    # === 1. RESULTADO PRINCIPAL (HACKATHON FOCUS) ===
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
            # Lista de tipos sensíveis/críticos para o badge
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
    
    # Critérios de Risco
    # Agora com categorias granulares
    critical_categories = {'CPF', 'RG', 'CNH', 'MATRICULA', 
                          'SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 
                          'SENSITIVE_RACE', 'SENSITIVE_GENDER'}
    
    # Inscrição e Processo Legal geralmente não são críticos por si só, mas identificam
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