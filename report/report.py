"""
Processador Standalone de PII - V10.0
Melhorias:
- Validação inteligente de CPF com busca de contexto
- Log profissional e limpo
- Regex de telefone blindado contra processos
- Categoria 'Registros Gerais' (RG, NIS, PIS, CNH, etc)
- Validação de contexto para telefones (evita falsos positivos)
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
    os.system("")  # Ativa suporte ANSI no CMD/PowerShell


# --- Configuração ---
FILE_NAME = './files/amostra_validacao_lgpd_v2.csv'
TARGET_COLUMN = 'Texto Mascarado'


class PIIDetector:
    """Detector de PII V10.0 com validação contextual de CPF"""
    
    PII_TYPES = {
        'PERSON_NAME': 'Nome de Pessoa',
        'CPF': 'Cadastro de Pessoa Física',
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Número de Telefone',
        'FULL_ADDRESS': 'Endereço Completo',
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

    # Palavras-chave que indicam CPF no contexto
    CPF_CONTEXT_KEYWORDS = [
        r'cpf', r'cadastro de pessoa f[íi]sica', r'inscri[çc][ãa]o', 
        r'inscrito no cpf', r'cpf n[úu]mero', r'cpf sob o n[úu]mero',
        r'portador do cpf', r'titular do cpf', r'contribuinte',
        r'documento cpf', r'cadastro cpf'
    ]

    def __init__(self):
        """Inicializa o detector com modelo SpaCy e padrões regex"""
        try:
            self.nlp = spacy.load("pt_core_news_lg")
            pipes_to_disable = ['parser', 'tagger', 'morphologizer', 'lemmatizer']
            existing_pipes = [p for p in pipes_to_disable if p in self.nlp.pipe_names]
            if existing_pipes:
                self.nlp.disable_pipes(existing_pipes)
        except OSError:
            self.nlp = None

        # Padrões de telefone (blindados contra processos + validação de contexto)
        self.phone_patterns = [
            # 1. Formatado: (XX) 9XXXX-XXXX ou (XX) 3XXX-XXXX
            r'\(([1-9]{2})\)\s?([9][0-9]{4}|[2-5][0-9]{3})-?[0-9]{4}\b',
            
            # 2. Semi-formatado: XX 9XXXX-XXXX  
            r'\b([1-9]{2})\s([9][0-9]{4}|[2-5][0-9]{3})-[0-9]{4}\b',
            
            # 3. Celular Solto Estrito: DDD[1-9]{2} + 9 + 8 digitos (Total 11)
            r'\b[1-9]{2}9\d{8}\b',
            
            # 4. Fixo Solto Estrito: DDD[1-9]{2} + [2-5] + 7 digitos (Total 10)
            r'\b[1-9]{2}[2-5]\d{7}\b',

            # 5. Contexto (Backup): Só aceita se tiver "tel/cel" antes
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,12}\b'
        ]

        self.regex_patterns = {
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|SRES|SHDF|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.)\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            # GENERAL_REGISTRY: Exclui números após "CPF" (isso é tratado separadamente)
            'GENERAL_REGISTRY': r'(?i)(?:RG|CNH|Matr[íi]cula|NIS|PIS|PASEP|NIT|CTPS|T[íi]tulo\s(?:de\s)?Eleitor)(?!\s*cpf)[:\s\.]+\d{1,15}[-\d]*|\b\d{3}\.\d{5}\.\d{2}-\d\b'
        }

        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [r'\bc[âa]ncer\b', r'\boncologia\b', r'\bhiv\b', r'\baids\b', r'\basm[áa]tico\b', r'\bminha doen[çc]a\b', r'\blaudo m[ée]dico\b', r'\bCID\s?[A-Z]\d', r'\btranstorno\b', r'\bdepress[ãa]o\b', r'\bdefici[êe]ncia\b', r'\bautis'],
            'SENSITIVE_MINOR': [r'\bmenor de idade\b', r'\bcrian[çc]a\b', r'\bfilh[ao] (?:de )?menor\b', r'\btutela\b', r'\bcreche\b', r'\balun[ao]\b'],
            'SENSITIVE_SOCIAL': [r'\bvulnerabilidade\b', r'\baux[íi]lio emergencial\b', r'\bcesta b[áa]sica\b', r'\bbolsa fam[íi]lia\b'],
            'SENSITIVE_RACE': [r'\bcor d[ae] pele\b', r'\braça\b', r'\betnia\b', r'\bnegro\b', r'\bpardo\b'],
            'SENSITIVE_GENDER': [r'\btrans\b', r'\bhormoniza[çc][ãa]o\b', r'\bidentidade de g[êe]nero\b']
        }

    def _validate_cpf_digit(self, cpf: str) -> bool:
        """Valida dígitos verificadores do CPF"""
        if len(cpf) != 11 or not cpf.isdigit():
            return False
        
        # CPFs inválidos conhecidos
        if cpf == cpf[0] * 11:
            return False
        
        # Valida primeiro dígito
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        
        if digito1 != int(cpf[9]):
            return False
        
        # Valida segundo dígito
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        
        return digito2 == int(cpf[10])

    def _has_cpf_context(self, text: str, position: int, window: int = 50) -> bool:
        """Verifica se há palavras-chave de CPF próximas à posição"""
        start = max(0, position - window)
        end = min(len(text), position + window)
        context = text[start:end].lower()
        
        return any(re.search(keyword, context, re.IGNORECASE) for keyword in self.CPF_CONTEXT_KEYWORDS)

    def _is_near_pii_keyword(self, text: str, position: int, window: int = 30) -> bool:
        """
        Verifica se o número está próximo de palavras-chave de outros PIIs.
        Retorna True se estiver perto de CPF, RG, CNPJ, etc (NÃO é telefone)
        
        IMPORTANTE: Ignora palavras de telefone (tel, contato, etc) para permitir
        casos válidos como "Contato: (11) 98765-4321"
        """
        start = max(0, position - window)
        end = min(len(text), position + window)
        context = text[start:end].lower()
        
        # Lista REFINADA: apenas PIIs que NÃO são telefone
        strict_pii_keywords = [
            r'\bcpf\b', r'\bcnpj\b', r'\brg\b', r'\bcnh\b', r'\bnis\b', r'\bpis\b',
            r'\bpasep\b', r'\bnit\b', r'\bctps\b', r'\bmatr[íi]cula\b',
            r'\bt[íi]tulo\s+eleitor\b', r'\binscri[çc][ãa]o\b',
            r'\bidentidade\b', r'\bdocumento\s+(?:de\s+)?identidade\b'
        ]
        
        return any(re.search(keyword, context, re.IGNORECASE) for keyword in strict_pii_keywords)

    def _detect_cpf(self, text: str) -> List[Tuple[int, int, bool]]:
        """
        Detecta CPFs com validação inteligente:
        1. CPF formatado (xxx.xxx.xxx-xx) → sempre detecta
        2. 11 dígitos soltos → detecta apenas se tiver contexto
        Retorna: lista de tuplas (start, end, is_valid)
        """
        cpf_matches = []
        detected_positions = set()
        
        # Padrão 1: CPF formatado (xxx.xxx.xxx-xx) - SEMPRE detecta
        formatted_pattern = r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'
        for match in re.finditer(formatted_pattern, text):
            cpf_digits = re.sub(r'\D', '', match.group())
            is_valid = self._validate_cpf_digit(cpf_digits)
            cpf_matches.append((match.start(), match.end(), is_valid))
            detected_positions.update(range(match.start(), match.end()))
        
        # Padrão 2: EXATAMENTE 11 dígitos soltos (PRECISA de contexto)
        loose_pattern = r'\b\d{11}\b'
        for match in re.finditer(loose_pattern, text):
            cpf_candidate = match.group()
            
            # Evita duplicatas (já detectado como formatado)
            if any(pos in detected_positions for pos in range(match.start(), match.end())):
                continue
            
            # OBRIGATÓRIO: Tem contexto de CPF próximo?
            has_context = self._has_cpf_context(text, match.start())
            
            if has_context:
                # Valida matematicamente para reportar no log
                is_valid = self._validate_cpf_digit(cpf_candidate)
                cpf_matches.append((match.start(), match.end(), is_valid))
                detected_positions.update(range(match.start(), match.end()))
        
        return cpf_matches

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int], Dict[str, int]]:
        """Detecta e mascara PII no texto. Retorna texto mascarado, stats e CPFs inválidos"""
        if pd.isna(text) or not isinstance(text, str):
            return text, {}, {}
        
        indices_to_mask = set()
        pii_stats = defaultdict(int)
        invalid_cpfs = defaultdict(int)
        
        # 1. CPF (com validação contextual)
        for start, end, is_valid in self._detect_cpf(text):
            indices_to_mask.update(range(start, end))
            pii_stats['CPF'] += 1
            if not is_valid:
                invalid_cpfs['CPF_INVALID'] += 1
        
        # 2. Outros padrões regex
        for pii_type, pattern in self.regex_patterns.items():
            for match in re.finditer(pattern, text):
                match_range = set(range(match.start(), match.end()))
                # Só adiciona se não houver sobreposição com algo já detectado
                if not match_range.intersection(indices_to_mask):
                    indices_to_mask.update(match_range)
                    pii_stats[pii_type] += 1

        # 3. Telefones (regex estrito + validação de contexto + Google lib)
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text):
                # NOVO: Valida se não está em contexto de outro PII
                if self._is_near_pii_keyword(text, match.start()):
                    continue  # Ignora: provavelmente é CPF/RG/CNPJ malformatado
                
                match_range = set(range(match.start(), match.end()))
                if not match_range.intersection(indices_to_mask):
                    indices_to_mask.update(match_range)
                    pii_stats['PHONE'] += 1
        
        try:
            for match in phonenumbers.PhoneNumberMatcher(text, "BR"):
                if phonenumbers.is_valid_number(match.number):
                    # NOVO: Valida contexto também para Google Phonenumbers
                    if self._is_near_pii_keyword(text, match.start):
                        continue
                    
                    match_range = set(range(match.start, match.end))
                    if not match_range.intersection(indices_to_mask):
                        indices_to_mask.update(match_range)
                        pii_stats['PHONE'] += 1
        except Exception:
            pass

        # 4. Dados sensíveis
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    indices_to_mask.update(range(match.start(), match.end()))
                    pii_stats[sens_type] += 1

        # 5. Nomes (NLP + IBGE)
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        name_candidate = ent.text.strip()
                        clean_name = re.sub(r'[^\w\s]', '', name_candidate.lower())
                        parts = clean_name.split()
                        
                        if len(parts) < 2:
                            continue
                        
                        has_common_part = any(p in self.COMMON_NAMES or p in self.COMMON_SURNAMES for p in parts)
                        has_honorific = re.search(r'(?i)\b(?:dr|dra|sr|sra)\.?\s', text[max(0, ent.start_char-5):ent.start_char])

                        if not has_common_part and not has_honorific:
                            continue

                        match_range = set(range(ent.start_char, ent.end_char))
                        if not match_range.intersection(indices_to_mask):
                            indices_to_mask.update(match_range)
                            pii_stats['PERSON_NAME'] += 1
            except Exception:
                pass

        # 6. Anonimização
        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask:
                redacted_chars.append('x' if char.isalnum() else char)
            else:
                redacted_chars.append(char)
        
        return "".join(redacted_chars), dict(pii_stats), dict(invalid_cpfs)

    def get_description(self, key: str) -> str:
        """Retorna descrição legível do tipo de PII"""
        return self.PII_TYPES.get(key, key)


class Logger:
    """Sistema de logging profissional com cores e formatação"""
    
    # Cores ANSI
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Cores de texto
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GREY = '\033[90m'
    
    # Cores de fundo
    BG_RED = '\033[101m'
    BG_YELLOW = '\033[103m'
    BG_GREEN = '\033[102m'
    
    @staticmethod
    def header(message: str):
        """Imprime cabeçalho principal"""
        print(f"\n{'=' * 80}")
        print(f"{Logger.BOLD}{Logger.CYAN}  {message}{Logger.RESET}")
        print(f"{'=' * 80}\n")
    
    @staticmethod
    def section(title: str):
        """Imprime título de seção"""
        print(f"\n{Logger.BOLD}{Logger.WHITE}{title}{Logger.RESET}")
        print(f"{Logger.DIM}{'─' * 80}{Logger.RESET}")
    
    @staticmethod
    def metric(label: str, value: str, alert: bool = False):
        """Imprime métrica formatada"""
        if alert:
            symbol = f"{Logger.RED}▲{Logger.RESET}"
            value_colored = f"{Logger.RED}{Logger.BOLD}{value}{Logger.RESET}"
        else:
            symbol = " "
            value_colored = f"{Logger.GREEN}{value}{Logger.RESET}"
        
        print(f"  {symbol} {label:<38} {value_colored:>20}")
    
    @staticmethod
    def category(name: str, count: int, is_sensitive: bool = False):
        """Imprime categoria de PII"""
        if is_sensitive:
            badge = f"{Logger.BG_RED}{Logger.WHITE} CRÍTICO {Logger.RESET}"
            bullet = f"{Logger.RED}●{Logger.RESET}"
        else:
            badge = f"{Logger.BG_YELLOW}{Logger.WHITE} ALERTA {Logger.RESET}"
            bullet = f"{Logger.YELLOW}●{Logger.RESET}"
        
        print(f"  {bullet} {badge} {Logger.BOLD}{name}{Logger.RESET} {Logger.DIM}({count} ocorrências){Logger.RESET}")
    
    @staticmethod
    def records(records_str: str):
        """Imprime lista de registros afetados"""
        print(f"    {Logger.GREY}└─ Registros: {records_str}{Logger.RESET}")
    
    @staticmethod
    def alert_box(message: str, level: str = "CRÍTICO"):
        """Imprime caixa de alerta destacada"""
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
        """Imprime informação"""
        spaces = " " * indent
        print(f"{spaces}{Logger.GREY}{message}{Logger.RESET}")
    
    @staticmethod
    def success(message: str):
        """Imprime mensagem de sucesso"""
        print(f"  {Logger.GREEN}✓{Logger.RESET} {message}")
    
    @staticmethod
    def warning(message: str):
        """Imprime aviso"""
        print(f"  {Logger.YELLOW}⚠{Logger.RESET} {Logger.BOLD}{message}{Logger.RESET}")
    
    @staticmethod
    def recommendation(message: str, is_critical: bool = False):
        """Imprime recomendação"""
        if is_critical:
            symbol = f"{Logger.RED}✗{Logger.RESET}"
        else:
            symbol = f"{Logger.YELLOW}⚠{Logger.RESET}"
        print(f"  {symbol} {message}")


def generate_report(df: pd.DataFrame, pii_details: dict, records_with_pii: int, 
                   processing_time: float, detector: PIIDetector, filename: str,
                   invalid_cpf_count: int, record_risk_analysis: dict):
    """Gera relatório profissional de análise LGPD"""
    
    logger = Logger()
    total_records = len(df)
    pii_rate = (records_with_pii / total_records * 100) if total_records > 0 else 0
    
    # Calcula totais por categoria
    pii_stats_total = {k: sum(item['qtd'] for item in v) for k, v in pii_details.items()}
    
    # Avaliação de risco
    sensitive_keys = ['SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 
                     'SENSITIVE_RACE', 'SENSITIVE_GENDER']
    has_sensitive = any(k in pii_stats_total for k in sensitive_keys)
    has_mass_ids = sum(pii_stats_total.get(k, 0) for k in ['CPF', 'CNPJ', 'GENERAL_REGISTRY']) > (total_records * 0.1)
    
    risk_level = "BAIXO"
    risk_message = "Poucos dados pessoais identificados."
    
    if has_sensitive or has_mass_ids:
        risk_level = "CRÍTICO"
        risk_message = "Dados sensíveis ou identificadores oficiais em massa detectados."
    elif records_with_pii > 0:
        risk_level = "ALTO"
        risk_message = "Identificadores pessoais detectados no dataset."
    
    # === CABEÇALHO ===
    logger.header(f"RELATÓRIO DE ANÁLISE LGPD - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info(f"Arquivo: {os.path.basename(filename)}", indent=0)
    logger.info(f"Processador: PII Detector v10.0", indent=0)
    
    # === ALERTA DE CLASSIFICAÇÃO ===
    if records_with_pii > 0:
        logger.alert_box(risk_message, risk_level)
    
    # === INDICADORES ===
    logger.section("INDICADORES DE PROCESSAMENTO")
    logger.metric("Total de registros analisados", f"{total_records:,}")
    logger.metric("Registros com dados sensíveis", f"{records_with_pii:,}", alert=records_with_pii > 0)
    logger.metric("Registros sem dados sensíveis", f"{total_records - records_with_pii:,}")
    logger.metric("Taxa de incidência", f"{pii_rate:.2f}%", alert=pii_rate > 10)
    logger.metric("Tempo de processamento", f"{processing_time:.2f}s")
    
    # === CLASSIFICAÇÃO INDIVIDUAL DOS REGISTROS ===
    logger.section("CLASSIFICAÇÃO INDIVIDUAL DOS REGISTROS")
    
    # Separa registros por nível de risco
    public_records = []
    moderate_records = []
    critical_records = []
    
    for record_id, risk_info in record_risk_analysis.items():
        if risk_info['level'] == 'PÚBLICO':
            public_records.append(record_id)
        elif risk_info['level'] == 'MODERADO':
            moderate_records.append(record_id)
        else:  # CRÍTICO
            critical_records.append(record_id)
    
    # Registros PÚBLICOS (podem ser divulgados)
    if public_records:
        logger.info(f"{Logger.GREEN}✓ REGISTROS PÚBLICOS{Logger.RESET} (podem ser divulgados sem restrições)", indent=2)
        logger.info(f"Total: {len(public_records)} registros", indent=4)
        
        # Mostra lista de IDs públicos
        public_ids_str = ", ".join([f"#{rid}" for rid in public_records[:20]])
        if len(public_records) > 20:
            public_ids_str += f" ... +{len(public_records) - 20}"
        logger.info(f"IDs: {public_ids_str}", indent=4)
        print()
    
    # Registros MODERADOS (requerem atenção)
    if moderate_records:
        logger.info(f"{Logger.YELLOW}⚠ REGISTROS COM RISCO MODERADO{Logger.RESET} (requerem revisão)", indent=2)
        logger.info(f"Total: {len(moderate_records)} registros", indent=4)
        logger.info(f"Contêm: dados pessoais não-sensíveis (e-mail, telefone, endereço)", indent=4)
        
        moderate_ids_str = ", ".join([f"#{rid}" for rid in moderate_records[:10]])
        if len(moderate_records) > 10:
            moderate_ids_str += f" ... +{len(moderate_records) - 10}"
        logger.info(f"IDs: {moderate_ids_str}", indent=4)
        print()
    
    # Registros CRÍTICOS (não podem ser divulgados)
    if critical_records:
        logger.info(f"{Logger.RED}✗ REGISTROS CRÍTICOS{Logger.RESET} (NÃO podem ser divulgados)", indent=2)
        logger.info(f"Total: {len(critical_records)} registros", indent=4)
        logger.info(f"Contêm: CPF, dados sensíveis, registros oficiais", indent=4)
        
        critical_ids_str = ", ".join([f"#{rid}" for rid in critical_records[:10]])
        if len(critical_records) > 10:
            critical_ids_str += f" ... +{len(critical_records) - 10}"
        logger.info(f"IDs: {critical_ids_str}", indent=4)
        
        # Detalha o motivo de cada registro crítico
        print()
        logger.info(f"{Logger.DIM}Detalhamento dos registros críticos:{Logger.RESET}", indent=4)
        for record_id in critical_records[:5]:  # Mostra detalhes dos 5 primeiros
            reasons = record_risk_analysis[record_id]['reasons']
            reasons_str = ", ".join(reasons)
            logger.info(f"  #{record_id}: {reasons_str}", indent=4)
        if len(critical_records) > 5:
            logger.info(f"  ... e mais {len(critical_records) - 5} registros", indent=4)
    
    # === DETALHAMENTO ===
    if pii_details:
        logger.section("DETALHAMENTO POR CATEGORIA DE DADOS")
        
        sorted_details = sorted(pii_details.items(), 
                               key=lambda x: sum(i['qtd'] for i in x[1]), 
                               reverse=True)
        
        for pii_type, occurrences in sorted_details:
            total_count = sum(item['qtd'] for item in occurrences)
            desc = detector.get_description(pii_type)
            
            # Verifica se é sensível
            is_sensitive = ("Sensível" in desc or pii_type in ['CPF', 'CNPJ', 'GENERAL_REGISTRY'])
            
            # Formata lista de registros (máximo 5)
            records_list = [f"#{item['id']} ({item['qtd']}x)" for item in occurrences[:5]]
            if len(occurrences) > 5:
                records_list.append(f"... +{len(occurrences) - 5}")
            records_str = ", ".join(records_list)
            
            logger.category(desc, total_count, is_sensitive)
            logger.records(records_str)
    else:
        logger.section("DETALHAMENTO POR CATEGORIA DE DADOS")
        logger.info("Nenhum dado pessoal identificado", indent=2)
    
    # === ALERTAS DE QUALIDADE ===
    if invalid_cpf_count > 0:
        logger.section("ALERTAS DE QUALIDADE")
        logger.warning(f"Detectados {invalid_cpf_count} CPF(s) com formato inválido")
        logger.info("Estes podem ser erros de digitação ou números fictícios", indent=4)
    
    # === RECOMENDAÇÕES ===
    logger.section("RECOMENDAÇÕES")
    
    if critical_records:
        logger.recommendation(f"REGISTROS CRÍTICOS (#{len(critical_records)}): Contêm dados sensíveis e NÃO devem ser divulgados", is_critical=True)
        logger.recommendation("Requer anonimização completa antes de qualquer compartilhamento", is_critical=True)
    
    if moderate_records:
        logger.recommendation(f"REGISTROS MODERADOS (#{len(moderate_records)}): Avaliar necessidade de anonimização", is_critical=False)
        logger.recommendation("Considere remover e-mails, telefones e endereços antes da divulgação", is_critical=False)
    
    if public_records:
        logger.success(f"REGISTROS PÚBLICOS (#{len(public_records)}): Podem ser divulgados sem restrições")
    
    print(f"\n{'=' * 80}\n")


def main():
    """Função principal de execução"""
    
    # Validação de arquivo
    if not os.path.exists(FILE_NAME):
        print(f"✗ Erro: Arquivo '{FILE_NAME}' não encontrado.")
        return
    
    # Inicialização
    print("Iniciando PII Detector v10.0...")
    detector = PIIDetector()
    
    # Carregamento de dados
    try:
        if FILE_NAME.endswith('.csv'):
            df = pd.read_csv(FILE_NAME)
        else:
            df = pd.read_excel(FILE_NAME)
        print(f"✓ Arquivo carregado: {len(df)} registros encontrados")
    except Exception as e:
        print(f"✗ Erro ao ler arquivo: {e}")
        return

    # Identificação de colunas
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

    # Processamento
    print(f"Processando coluna '{target_col}'...", end=' ', flush=True)
    start_time = time.time()
    
    pii_details = defaultdict(list)
    records_with_pii = 0
    total_invalid_cpfs = 0
    record_risk_analysis = {}  # Análise de risco por registro
    
    # Categorias críticas (impedem publicação)
    critical_categories = {'CPF', 'CNPJ', 'GENERAL_REGISTRY', 'SENSITIVE_HEALTH', 
                          'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 'SENSITIVE_RACE', 
                          'SENSITIVE_GENDER'}
    
    # Categorias moderadas (requerem atenção)
    moderate_categories = {'EMAIL', 'PHONE', 'FULL_ADDRESS', 'PERSON_NAME'}

    for idx, row in df.iterrows():
        text_content = str(row[target_col])
        _, stats, invalid_stats = detector.detect_and_redact(text_content)
        
        record_id = row[id_col] if id_col else f"Linha_{idx + 2}"
        
        # Análise de risco individual
        if stats:
            records_with_pii += 1
            
            # Classifica o risco deste registro específico
            has_critical = any(cat in stats for cat in critical_categories)
            has_moderate = any(cat in stats for cat in moderate_categories)
            
            if has_critical:
                # Identifica quais dados críticos foram encontrados
                critical_found = [detector.get_description(cat) for cat in stats.keys() 
                                 if cat in critical_categories]
                record_risk_analysis[record_id] = {
                    'level': 'CRÍTICO',
                    'reasons': critical_found
                }
            elif has_moderate:
                moderate_found = [detector.get_description(cat) for cat in stats.keys() 
                                 if cat in moderate_categories]
                record_risk_analysis[record_id] = {
                    'level': 'MODERADO',
                    'reasons': moderate_found
                }
            
            for pii_type, count in stats.items():
                pii_details[pii_type].append({'id': record_id, 'qtd': count})
            
            # Conta CPFs inválidos
            if 'CPF_INVALID' in invalid_stats:
                total_invalid_cpfs += invalid_stats['CPF_INVALID']
        else:
            # Registro sem PII = público
            record_risk_analysis[record_id] = {
                'level': 'PÚBLICO',
                'reasons': []
            }
    
    processing_time = time.time() - start_time
    print("Concluído ✓")

    # Geração de relatório
    generate_report(df, pii_details, records_with_pii, processing_time, detector, 
                   FILE_NAME, total_invalid_cpfs, record_risk_analysis)


if __name__ == "__main__":
    main()