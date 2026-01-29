"""
Processador Standalone de PII - V15.4 (ROLLBACK NOMES)
Ajustes:
1. Nomes: Revertido para lógica V15.2 (Exige Nome+Sobrenome ou Gatilho Forte). Assinaturas soltas removidas.
2. Endereço: Mantida a expansão para SHDF/Rodovias/Lotes (ID 18/59).
3. Telefone: Mantida validação ANATEL (ID 84).
4. NIS: Mantida validação estrita (ID 97).
"""
import pandas as pd
import spacy
import re
import os
import time
from collections import defaultdict
from typing import Dict, Tuple, List
from datetime import datetime
import sys

# Configuração de Ambiente
if sys.platform == "win32":
    os.system("")

FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
TARGET_COLUMN = 'Texto Mascarado'

class PIIDetector:
    
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

    # DDDs válidos no Brasil (ANATEL)
    VALID_DDDS = {
        11,12,13,14,15,16,17,18,19,21,22,24,27,28,31,32,33,34,35,37,38,
        41,42,43,44,45,46,47,48,49,51,53,54,55,61,62,64,63,65,66,67,68,69,
        71,73,74,75,77,79,81,87,82,83,84,85,88,86,89,91,93,94,92,97,95,96,98,99
    }

    COMMON_FIRST_NAMES = {
        'ana','maria','joao','jose','antonio','francisco','carlos','paulo','pedro','lucas',
        'luiz','marcos','luis','gabriel','rafael','daniel','marcelo','bruno','eduardo',
        'felipe','raimundo','rodrigo','manoel','mateus','andre','fernando','guilherme',
        'gustavo','julio','leonardo','thiago','tiago','alexandre','adriano','claudio',
        'marcio','roberto','fabio','sergio','ricardo','luciano','jorge','samuel','filipe',
        'hugo','diego','vitor','vinicius','caio','david','otavio','robson','matheus',
        'fatima','patricia','aline','sandra','camila','amanda','bruna','jessica','leticia',
        'julia','luciana','vanessa','mariana','gabriela','beatriz','fernanda','regina',
        'renata','priscila','jaqueline','cristiane','caroline','daniela','raquel','erica',
        'bianca','larissa','debora','natalia','cristina','simone','eliane','lucio','miguel',
        'arthur','davi','heitor','theo','bernardo','enzo','lorenzo','benjamin','isaac',
        'breno','emanuel','ryan','yuri','leandro','igor','mauro','henrique','renan',
        'helena','alice','laura','sophia','manuela','valentina','sophie','isabella',
        'heloisa','luiza','cecilia','eloa','livia','lorena','antonella','maite','isadora',
        'sarah','marina','clara','melissa','yasmin','bela','giovana','ester','elisa',
        'ruth','walter','aura','lima','tavares','betina','conceicao','pablo'
    }

    COMMON_SURNAMES = {
        'silva','santos','oliveira','souza','rodrigues','ferreira','alves','pereira','lima',
        'gomes','costa','ribeiro','martins','carvalho','almeida','lopes','soares','fernandes',
        'vieira','barbosa','rocha','dias','nascimento','andrade','moreira','nunes','marques',
        'machado','mendes','freitas','cardoso','ramos','goncalves','santana','teixeira',
        'cavalcanti','moura','campos','jesus','pinto','araujo','leite','barros','farias',
        'cunha','reis','siqueira','moraes','castro','batista','neves','rosa','medeiros',
        'dantas','conceicao','braga','filho','neto','junior','sobrinho','mota','vasconcelos',
        'cruz','viana','peixoto','maia','monteiro','coelho','correia','brito','tavares',
        'xavier','franco','maciel','sales','guimaraes','garcia','valle','simoes','camargo',
        'sousa','barreto','benicio','vitoria','fontes','muniz','fagundes','chaves','paiva',
        'sampaio','lacerda'
    }

    INVALID_NAME_TERMS = {
        'ltda','s/a','s.a','sa','me','epp','inc','advogados','associados','engenharia',
        'construcoes','empreendimentos','participacoes','comercio','servicos','solucoes',
        'tecnologia','group','systems','sistema','educacional','imobiliaria','turismo',
        'edital','concurso','candidato','auditor','vencimento','padrao','cargo','licenca',
        'ferias','uniao','estados','municipios','ente','federativo','certame','estrutura',
        'despacho','consulta','legislacao','valor','ajuda','financeira','matricula',
        'viabilidade','junta','comercial','usuario','taxa','exigencia','natureza','juridica',
        'constante','referencia','pendencia','nota','explicativa','nire','protocolo',
        'agencia','comite','comissao','assessoria','regiao','setor','box','ambiente',
        'secretaria','ministerio','departamento','diretoria','gerencia','coordenacao',
        'superintendencia','prefeitura','governo','estado','distrito','tribunal',
        'igreja','sistema','termo','acordo','cooperacao','programa','plano','projeto',
        'fundo','grupo','centro','nucleo','camara','assembleia','sindicato','associacao',
        'fundacao','instituto','hospital','clinica','escola','colegio','faculdade',
        'universidade','policia','delegacia','batalhao','comando','corpo','defensoria',
        'promotoria','procuradoria','cartorio','oficio','servico','serviço','area',
        'razao','social','nome','fantasia','assunto','descricao','motivo','justificativa',
        'documento','certidao','portaria','decreto','lei','artigo','inciso','item',
        'efetivo','empresarial','civil','militar','atenciosamente'
    }

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
            'LEGAL_PROCESS': r'\b\d{4,7}[-.]\d{2}[-.]\d{4}[-.]\d[-.]\d{2}[-.]\d{4}\b|\b\d{20}\b|\b\d{4,5}[-.]\d{8,10}[/.]\d{4}[-.]\d{2}\b',
            'PROTOCOL': r'\b(?:LAI|PROTOCOLO|OUVIDORIA|SEI|CHAMADO)[-:\s.]+\d{1,15}[-./]?\d{0,10}[-./]?\d{0,4}\b',
            'PROPERTY_REG': r'(?i)(?:inscri[çc][ãa]o imobili[áa]ria|im[óo]vel|matr[íi]cula do im[óo]vel)[\snº\.:]+(\d+)',
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'CEP': r'\b\d{5}\s*[-]\s*\d{3}\b', 
            # Endereço Expandido (SHDF, Rodovia, Lote...)
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|SQN|SQS|SHN|SHS|CLN|CRN|SAS|ER ES|ER ES|Cond\.|Bloco|Bl\.|Lote|Lt\.|Lt|Al\.|Alameda|Logradouro|SHDF|Ap\.|Apartamento)\s+[\w\s\.,-]{1,100}(?:(?:\b\d{1,5}\b|[A-Z]\b))',
            'MATRICULA': r'(?i)\b(?:Matr[íi]cula|Siape)(?!\s+do im[óo]vel)[:\s\.]+(?=\w*\d)(\w{1,15}[-.\s]?\w{0,2})\b',
            'INSCRICAO': r'(?i)\b(?:Inscri[çc][ãa]o)(?!\s+imobili[áa]ria)[:\s\.]+(\d{1,15}[-.\s]?\d{0,2})\b',
            'RG': r'(?i)(?:RG|R\.G\.|Identidade)[:\s\.]+(\d{1,2}\.?\d{3}\.?\d{3}[-.\s]?[\dX])\b',
            'CNH': r'(?i)(?:CNH|Habilita[çc][ãa]o)[:\s\.]+(\d{9,11})\b',
        }
        
        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [r'\bdiagn[oó]stico d[eo]\b', r'\bportador d[eo] (?:c[âa]ncer|hiv|aids|defici[êe]ncia)\b', r'\blaudo m[ée]dico\b', r'\bCID\s?[A-Z]\d', r'\btranstorno\b'],
            'SENSITIVE_MINOR': [r'\bmenor de idade\b', r'\btutela d[eo] menor\b', r'\bguarda d[oa] crian[çc]a\b', r'\bcertid[ãa]o de nascimento\b'],
            'SENSITIVE_SOCIAL': [r'\bvulnerabilidade social\b', r'\bbenefici[áa]rio do (?:bolsa|aux[íi]lio)\b'],
            'SENSITIVE_RACE': [r'\bautodeclara[çc][ãa]o de cor\b', r'\bcor d[ae] pele\b'],
            'SENSITIVE_GENDER': [r'\bnome social\b', r'\bidentidade de g[êe]nero\b']
        }

    # --- VALIDAÇÃO DE NOME ---
    def validar_nome_pessoa(self, nome_candidato):
        if not nome_candidato: return False
        nome = nome_candidato.strip()
        for termo in self.INVALID_NAME_TERMS:
            if re.search(r'\b' + re.escape(termo) + r'\b', nome, re.IGNORECASE):
                return False
        return True

    # --- VALIDAÇÃO DE CPF (FUNÇÃO MANTIDA) ---
    def _validate_cpf_digit(self, cpf: str) -> bool:
        if len(cpf) != 11 or not cpf.isdigit(): return False
        if cpf == cpf[0] * 11: return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf[9]): return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        return digito2 == int(cpf[10])
    
    def _is_blocked_by_nis(self, text: str, start: int, end: int) -> bool:
        """Verifica se há NIS/PIS/NIT/PASEP imediatamente antes do número"""
        # Janela de 10 caracteres antes
        before = text[max(0, start-10):start].upper()
        
        blockers = ['NIS', 'PIS', 'PASEP', 'NIT']
        
        # Verifica se algum bloqueador está na janela imediata
        for b in blockers:
            if b in before:
                return True
        return False

    def _has_cpf_context(self, text: str, position: int) -> bool:
        janela = text[max(0, position - 50):min(len(text), position + 50)].lower()
        return any(re.search(kw, janela, re.IGNORECASE) for kw in [r'cpf', r'cadastro', r'inscri[çc][ãa]o', r'documento'])

    def _detect_cpf(self, text: str) -> List[Tuple[int, int, bool]]:
        cpf_matches = []
        detected_positions = set()
        
        # CPF Formatado
        for match in re.finditer(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', text):
            if self._is_blocked_by_nis(text, match.start(), match.end()): continue
            cpf_digits = re.sub(r'\D', '', match.group())
            cpf_matches.append((match.start(), match.end(), self._validate_cpf_digit(cpf_digits)))
            detected_positions.update(range(match.start(), match.end()))
            
        # CPF 11 dígitos
        for match in re.finditer(r'\b\d{11}\b', text):
            if any(pos in detected_positions for pos in range(match.start(), match.end())): continue
            
            # Bloqueio estrito de NIS (só atrás)
            if self._is_blocked_by_nis(text, match.start(), match.end()): continue
            
            if self._has_cpf_context(text, match.start()):
                cpf_matches.append((match.start(), match.end(), self._validate_cpf_digit(match.group())))
        return cpf_matches

    # --- VALIDAÇÃO DE TELEFONE (ANATEL) ---
    def _is_valid_phone_structure(self, phone_text: str) -> bool:
        digits = re.sub(r'\D', '', phone_text)
        
        # ID 84 e 59: Validação Rigorosa
        if len(digits) not in [10, 11]: return False 
        
        try:
            ddd = int(digits[:2])
            first_num = int(digits[2])
            
            # 1. DDD Existe?
            if ddd not in self.VALID_DDDS: return False
            
            # 2. Regra do 1º Dígito (Celular = 9, Fixo = 2 a 5)
            if len(digits) == 11: 
                if first_num != 9: return False # Celular DEVE começar com 9
            elif len(digits) == 10:
                if first_num < 2 or first_num > 5: return False # Fixo
            
            return True
        except:
            return False

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int], Dict[str, int]]:
        if pd.isna(text) or not isinstance(text, str):
            return text, {}, {}
        
        indices_to_mask = set()
        protected_indices = set()
        detected_items = [] 
        invalid_cpfs = defaultdict(int)
        detected_names_ranges = set()

        # 1. Blindagem
        for blind_type in ['LEGAL_PROCESS', 'PROTOCOL', 'PROPERTY_REG']:
            for match in re.finditer(self.regex_patterns[blind_type], text):
                protected_indices.update(range(match.start(), match.end()))

        # 2. CPF (Com lógica anti-NIS corrigida)
        for start, end, is_valid in self._detect_cpf(text):
            if not protected_indices.intersection(range(start, end)):
                indices_to_mask.update(range(start, end))
                detected_items.append((start, end, 'CPF'))
                if not is_valid: invalid_cpfs['CPF_INVALID'] += 1

        # 3. Nomes (Gatilhos - VOLTANDO AO PADRÃO)
        # Removida lógica de assinatura solta (Grato/Att sem contexto forte)
        trigger_pattern = r'(?i:(?:Nome|Responsável|Interessado|Requerente|Servidor|Paciente|Aluno|Pai|Mãe|Me chamo|Sou|Eu\,|Att\.?|Atenciosamente|Procurador|Representante|Advogado))[:\s,]+([A-Z][a-zÀ-ÿ]+(?:\s+(?:da|de|do|dos|das|e)\s+)?(?:[A-Z][a-zÀ-ÿ]+)*)'
        
        for match in re.finditer(trigger_pattern, text):
            if not match.group(1): continue
            start_name, end_name = match.span(1)
            name_text = match.group(1)
            
            is_valid = False
            parts = name_text.split()
            
            # Lógica Padrão: 2 nomes ou 1 nome se for gatilho de apresentação
            if len(parts) >= 2:
                is_valid = self.validar_nome_pessoa(name_text)
            elif len(parts) == 1 and name_text.lower() in self.COMMON_FIRST_NAMES:
                trigger_word = text[match.start():start_name].lower()
                if any(w in trigger_word for w in ['sou', 'chamo', 'eu']): # Apenas apresentação
                    is_valid = True

            if is_valid and not protected_indices.intersection(range(start_name, end_name)):
                indices_to_mask.update(range(start_name, end_name))
                detected_names_ranges.update(range(start_name, end_name))
                detected_items.append((start_name, end_name, 'PERSON_NAME'))

        # 4. Nomes (Fallback - Exige Sobrenome)
        fallback_pattern = r'\b((?:[A-Z][a-zçáéíóúãõâêôÀ-ÿ]+|[A-Z]{1,3})(?:\s(?:da|de|do|dos|das|e)\s|\s)(?:[A-Z][a-zçáéíóúãõâêôÀ-ÿ]+|[A-Z]{1,3})(?:(?:\s(?:da|de|do|dos|das|e)\s|\s)(?:[A-Z][a-zçáéíóúãõâêôÀ-ÿ]+|[A-Z]{1,3}))*)\b'
        for match in re.finditer(fallback_pattern, text):
            start, end = match.span()
            name_text = match.group(1)
            if set(range(start, end)).intersection(detected_names_ranges): continue
            
            lookback_window = text[max(0, start-30):start].lower()
            if any(t in lookback_window for t in ['rua', 'av', 'avenida', 'bairro', 'cidade', 'logradouro']): continue
            
            lookahead_window = text[end:min(len(text), end+20)].lower()
            if any(t in lookahead_window for t in ['ltda', 's/a', 's.a', 'me', 'epp']): continue

            has_common = (any(p in self.COMMON_SURNAMES for p in name_text.lower().split()) or 
                          any(p in self.COMMON_FIRST_NAMES for p in name_text.lower().split()))
            
            if has_common and self.validar_nome_pessoa(name_text):
                if not protected_indices.intersection(range(start, end)):
                    indices_to_mask.update(range(start, end))
                    detected_names_ranges.update(range(start, end))
                    detected_items.append((start, end, 'PERSON_NAME'))

        # 5. Outros
        other_patterns = ['MATRICULA', 'INSCRICAO', 'RG', 'CNH', 'CNPJ', 'CEP', 'EMAIL', 'FULL_ADDRESS', 'PHONE']
        for p_type in other_patterns:
            if p_type not in self.regex_patterns and p_type != 'PHONE': continue 
            if p_type == 'PHONE': continue 
            
            pat = self.regex_patterns[p_type]
            for match in re.finditer(pat, text):
                start, end = match.span(1) if match.groups() else match.span()
                if not protected_indices.intersection(range(start, end)) and \
                   not set(range(start, end)).intersection(indices_to_mask):
                    indices_to_mask.update(range(start, end))
                    detected_items.append((start, end, p_type))

        # 6. Telefone (Validação ANATEL + Bloqueio CDA)
        phone_pats = [r'\b(?:\(?\s*0?([1-9][0-9])\s*\)?\s?)?(?:9\s?\d{4}[-.\s]?\d{4}|\d{4}[-.\s]?\d{4})\b']
        for pat in phone_pats:
            for match in re.finditer(pat, text):
                start, end = match.span()
                if re.search(r'(?:19|20)\d{2}$', match.group().strip()): continue
                
                # Contexto Negativo (ID 84 - Certidão/CDA)
                lookback = text[max(0, start-40):start].lower()
                if any(t in lookback for t in ['nire', 'protocolo', 'processo', 'sei', 'lai', 'cda', 'certidao', 'divida', 'gerador', 'ac']):
                    continue
                
                # Validação Lógica (ID 84 - Regra ANATEL)
                phone_candidate = match.group()
                digits = re.sub(r'\D', '', phone_candidate)
                if len(digits) >= 10 and not self._is_valid_phone_structure(digits):
                    continue

                if not protected_indices.intersection(range(start, end)) and \
                   not set(range(start, end)).intersection(indices_to_mask):
                    indices_to_mask.update(range(start, end))
                    detected_items.append((start, end, 'PHONE'))
                    
        # 7. Dados Sensíveis (Com Correção Gênero ID 99)
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    # ID 99: Ignora "Nome Social" se for instrução/lei ou não tiver valor preenchido
                    if sens_type == 'SENSITIVE_GENDER':
                         snippet = text[max(0, match.start()-60):min(len(text), match.end()+60)].lower()
                         if any(t in snippet for t in ['lei', 'decreto', 'artigo', 'dispõe', 'preencher', 'campo', 'caso possua', 'informar', 'se houver', 'uso do nome social']):
                             continue
                         # Se o termo está solto, sem dois pontos ou valor, ignora
                         next_chars = text[match.end():min(len(text), match.end()+5)]
                         if ':' not in next_chars and not any(c.isupper() for c in next_chars):
                             continue

                    if not protected_indices.intersection(range(match.start(), match.end())):
                        indices_to_mask.update(range(match.start(), match.end()))
                        detected_items.append((match.start(), match.end(), sens_type))

        # 8. Mesclagem Final
        detected_items.sort(key=lambda x: x[0])
        merged_stats = defaultdict(int)
        
        if detected_items:
            refined_items = []
            curr_s, curr_e, curr_t = detected_items[0]
            for i in range(1, len(detected_items)):
                next_s, next_e, next_t = detected_items[i]
                gap_text = text[curr_e:next_s]
                should_merge = False
                if curr_t == next_t:
                    if curr_t == 'PERSON_NAME':
                        if re.match(r'^\s+(?:e|da|de|do|dos|das)?\s*$', gap_text, re.IGNORECASE): should_merge = True
                    else:
                        if len(gap_text) < 5 and not re.search(r'[\n;,]', gap_text): should_merge = True
                if should_merge:
                    curr_e = max(curr_e, next_e)
                    indices_to_mask.update(range(curr_e, next_s)) 
                else:
                    refined_items.append((curr_s, curr_e, curr_t))
                    curr_s, curr_e, curr_t = next_s, next_e, next_t
            refined_items.append((curr_s, curr_e, curr_t))
            for _, _, t in refined_items: merged_stats[t] += 1
                
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
    def info(message: str, indent: int = 2):
        print(f"{' ' * indent}{Logger.GREY}{message}{Logger.RESET}")
    
    @staticmethod
    def warning(message: str):
        print(f"  {Logger.YELLOW}⚠{Logger.RESET} {Logger.BOLD}{message}{Logger.RESET}")

def generate_report(df: pd.DataFrame, pii_details: dict, records_with_pii: int, 
                    processing_time: float, detector: PIIDetector, filename: str,
                    invalid_cpf_count: int, record_risk_analysis: dict):
    
    logger = Logger()
    total_records = len(df)
    
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

    logger.header(f"ANÁLISE DE PEDIDOS - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info(f"Arquivo: {os.path.basename(filename)}", indent=0)
    logger.info(f"Processador: PII Detector v15.4 (Stable Rollback)", indent=0)
    
    logger.section("INDICADORES DE PROCESSAMENTO")
    pii_rate = (records_with_pii / total_records * 100) if total_records > 0 else 0
    logger.metric("Total de registros analisados", f"{total_records:,}")
    logger.metric("Registros com dados pessoais", f"{records_with_pii:,}", alert=records_with_pii > 0)
    logger.metric("Registros sem dados pessoais", f"{total_records - records_with_pii:,}")
    logger.metric("Taxa de incidência", f"{pii_rate:.2f}%", alert=pii_rate > 10)
    logger.metric("Tempo de processamento", f"{processing_time:.2f}s")

    print(f"\n{'=' * 80}\n")
    print(f"\n{Logger.BOLD}{Logger.WHITE}RESULTADO PRINCIPAL{Logger.RESET}")
    print(f"{Logger.DIM}{'─' * 80}{Logger.RESET}")

    print(f"\n{Logger.GREEN}PEDIDOS PÚBLICOS{Logger.RESET}")
    print(f"  (Podem ser divulgados - Sem informações pessoais)")
    print(f"  Total: {len(public_records)}")
    if public_records:
        ids_str = ', '.join([str(rid) for rid in public_records])
        print(f"  {Logger.GREY}IDs: {ids_str}{Logger.RESET}")
    
    print(f"\n{Logger.RED}PEDIDOS NÃO PÚBLICOS (Informações Pessoais){Logger.RESET}")
    print(f"  (Todos os pedidos que contenham informações pessoais)")
    print(f"  Total: {len(non_public_records)}")
    if non_public_records:
        ids_str = ', '.join([str(rid) for rid in non_public_records])
        print(f"  {Logger.GREY}IDs: {ids_str}{Logger.RESET}")
        
    print(f"\n{'=' * 80}\n")
    
    logger.section("CLASSIFICAÇÃO INDIVIDUAL DOS REGISTROS")
    
    if public_records:
        logger.info(f"{Logger.GREEN}✓ REGISTROS PÚBLICOS{Logger.RESET} (podem ser divulgados)", indent=2)
        logger.info(f"Total: {len(public_records)}", indent=4)
        print()
    
    if moderate_records:
        logger.info(f"{Logger.YELLOW}⚠ REGISTROS COM RISCO MODERADO{Logger.RESET} (requerem revisão)", indent=2)
        logger.info(f"Total: {len(moderate_records)}", indent=4)
        logger.info(f"IDs: {', '.join([str(rid) for rid in moderate_records])}", indent=4)
        print()
    
    if critical_records:
        logger.info(f"{Logger.RED}✗ REGISTROS CRÍTICOS{Logger.RESET} (NÃO divulgar)", indent=2)
        logger.info(f"Total: {len(critical_records)}", indent=4)
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