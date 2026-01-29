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
    """Detector de PII V26.0 - Expanded Dictionary & Bureaucracy Filter"""
    
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

    # --- 1. DICIONÁRIO EXPANDIDO (Resolve Caso 13: Lúcio Miguel) ---
    # Adicionei muito mais nomes para garantir que a Âncora funcione.
    
    COMMON_FIRST_NAMES = {
        'ana', 'maria', 'joao', 'jose', 'antonio', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas',
        'luiz', 'marcos', 'luis', 'gabriel', 'rafael', 'daniel', 'marcelo', 'bruno', 'eduardo',
        'felipe', 'raimundo', 'rodrigo', 'manoel', 'mateus', 'andre', 'fernando', 'guilherme',
        'gustavo', 'julio', 'leonardo', 'thiago', 'tiago', 'alexandre', 'adriano', 'claudio',
        'marcio', 'roberto', 'fabio', 'sergio', 'ricardo', 'luciano', 'jorge', 'samuel', 'filipe',
        'hugo', 'diego', 'vitor', 'vinicius', 'caio', 'david', 'otavio', 'robson', 'matheus',
        'fatima', 'patricia', 'aline', 'sandra', 'camila', 'amanda', 'bruna', 'jessica', 'leticia',
        'julia', 'luciana', 'vanessa', 'mariana', 'gabriela', 'beatriz', 'fernanda', 'regina',
        'renata', 'priscila', 'jaqueline', 'cristiane', 'caroline', 'daniela', 'raquel', 'erica',
        'bianca', 'larissa', 'debora', 'natalia', 'cristina', 'simone', 'eliane', 'lucio', 'miguel',
        'arthur', 'davi', 'heitor', 'theo', 'bernardo', 'enzo', 'lorenzo', 'benjamin', 'isaac',
        'breno', 'emanuel', 'ryan', 'yuri', 'leandro', 'igor', 'mauro', 'henrique', 'renan',
        'helena', 'alice', 'laura', 'sophia', 'manuela', 'valentina', 'sophie', 'isabella',
        'heloisa', 'luiza', 'cecilia', 'eloa', 'livia', 'lorena', 'antonella', 'maite', 'isadora',
        'sarah', 'marina', 'clara', 'melissa', 'yasmin', 'bela', 'giovana', 'ester', 'elisa'
    }

    COMMON_SURNAMES = {
        'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira', 'alves', 'pereira', 'lima',
        'gomes', 'costa', 'ribeiro', 'martins', 'carvalho', 'almeida', 'lopes', 'soares', 'fernandes',
        'vieira', 'barbosa', 'rocha', 'dias', 'nascimento', 'andrade', 'moreira', 'nunes', 'marques',
        'machado', 'mendes', 'freitas', 'cardoso', 'ramos', 'goncalves', 'santana', 'teixeira',
        'cavalcanti', 'moura', 'campos', 'jesus', 'pinto', 'araujo', 'leite', 'barros', 'farias',
        'cunha', 'reis', 'siqueira', 'moraes', 'castro', 'batista', 'neves', 'rosa', 'medeiros',
        'dantas', 'conceicao', 'braga', 'filho', 'neto', 'junior', 'sobrinho', 'mota', 'vasconcelos',
        'cruz', 'viana', 'peixoto', 'maia', 'monteiro', 'coelho', 'correia', 'brito', 'tavares',
        'xavier', 'franco', 'maciel', 'sales', 'guimarães', 'garcia', 'valle', 'simoes', 'camargo',
        'sousa', 'barreto', 'benicio', 'vitoria', 'fontes', 'muniz', 'fagundes', 'chaves', 'paiva'
    }

    # --- 2. LISTAS DE BLOQUEIO BUROCRÁTICO (Resolve Casos 93 e 62) ---
    
    INVALID_START_TERMS = {
        # Termos do Caso 93 (Edital, Concurso, Auditor)
        'edital', 'concurso', 'candidato', 'auditor', 'vencimento', 'padrao', 'cargo', 'licenca',
        'ferias', 'uniao', 'estados', 'municipios', 'ente', 'federativo', 'certame', 'estrutura',
        'despacho', 'consulta', 'legislacao', 'valor', 'ajuda', 'financeira', 'matricula',
        
        # Termos do Caso 62 (Viabilidade, Junta, Usuário)
        'viabilidade', 'junta', 'comercial', 'usuario', 'taxa', 'exigencia', 'natureza', 'juridica',
        'constante', 'referencia', 'pendencia', 'nota', 'explicativa', 'nire', 'protocolo',
        
        # Instituições e Genéricos (Mantidos da V25)
        'agencia', 'comite', 'comissao', 'assessoria', 'regiao', 'setor', 'box', 'ambiente',
        'secretaria', 'ministerio', 'departamento', 'diretoria', 'gerencia', 'coordenacao',
        'superintendencia', 'prefeitura', 'governo', 'estado', 'distrito', 'tribunal',
        'igreja', 'sistema', 'termo', 'acordo', 'cooperacao', 'programa', 'plano', 'projeto',
        'fundo', 'grupo', 'centro', 'nucleo', 'camara', 'assembleia', 'sindicato', 'associacao',
        'fundacao', 'instituto', 'hospital', 'clinica', 'escola', 'colegio', 'faculdade',
        'universidade', 'policia', 'delegacia', 'batalhao', 'comando', 'corpo', 'defensoria',
        'promotoria', 'procuradoria', 'cartorio', 'oficio', 'servico', 'serviço', 'area',
        
        # Ruído
        'prezados', 'caros', 'senhores', 'ola', 'alo', 'boa', 'bom', 'tarde', 'noite', 'dia',
        'segue', 'anexo', 'consta', 'ref', 'referente', 'trata', 'solicito', 'venho', 'informar',
        'requerer', 'encaminhar', 'agradeco', 'grato', 'obrigado', 'aguardo', 'retorno',
        'atenciosamente', 'respeitosamente', 'cordialmente', 'att', 'diante', 'visto', 'alem',
        'disso', 'havendo', 'assim', 'entende', 'face', 'pois', 'pelo', 'nesta', 'deste',
        
        # Administrativo
        'razao', 'social', 'nome', 'fantasia', 'assunto', 'descricao', 'motivo', 'justificativa',
        'data', 'local', 'qtde', 'unid', 'documento', 'certidao', 'portaria',
        'decreto', 'lei', 'artigo', 'inciso', 'item', 'fiscal', 'bairro', 'cidade',
        'pais', 'cep', 'endereco', 'logradouro', 'rua', 'avenida', 'travessa',
        'alameda', 'praca', 'largo', 'rodovia', 'estrada', 'quadra', 'lote', 'conjunto',
        'bloco', 'apartamento', 'sala', 'loja', 'condominio', 'edificio', 'residencial',
        'torre', 'vila', 'jardim', 'parque'
    }

    COMPANY_SUFFIXES = {
        'ltda', 's/a', 's.a', 'sa', 'me', 'epp', 'inc', 'advogados', 'associados', 'engenharia',
        'construcoes', 'empreendimentos', 'participacoes', 'comercio', 'servicos', 'solucoes',
        'tecnologia', 'group', 'systems', 'sistema', 'educacional', 'imobiliaria', 'turismo'
    }
    
    # Adicionado para bloquear "União" ou "Estados" no meio do texto
    INVALID_MID_TERMS = {
        'uniao', 'estados', 'municipios', 'viabilidade', 'junta', 'edital'
    }

    CONTEXT_BLOCKERS = {
        'rua', 'avenida', 'av', 'travessa', 'alameda', 'al', 'praca', 'praça',
        'largo', 'rodovia', 'estrada', 'bairro', 'zona', 'setor', 'quadra', 'lote',
        'conjunto', 'condominio', 'condomínio', 'edificio', 'edifício', 'residencial',
        'torre', 'bloco', 'apartamento', 'sala', 'loja', 'localizacao', 'municipio',
        'cidade', 'estado', 'pais', 'cep', 'endereco', 'logradouro',
        'programa', 'plano', 'projeto', 'gestao', 'gestão', 'politica', 'política',
        'unidade', 'orgao', 'órgão', 'entidade', 'empresa', 'firma', 'sociedade',
        'banco', 'caixa', 'colegio', 'escola', 'hospital', 'clinica'
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
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.|Al\.|Alameda)\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            'MATRICULA': r'(?i)\b(?:Matr[íi]cula|Siape)(?!\s+do im[óo]vel)[:\s\.]+(\w{1,15}[-.\s]?\w{0,2})\b',
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
        return any(re.search(kw, text[max(0, position - window):min(len(text), position + window)].lower(), re.IGNORECASE) 
                   for kw in [r'cpf', r'cadastro', r'inscri[çc][ãa]o', r'documento'])

    def _detect_cpf(self, text: str) -> List[Tuple[int, int, bool]]:
        cpf_matches = []
        detected_positions = set()
        for match in re.finditer(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', text):
            cpf_digits = re.sub(r'\D', '', match.group())
            cpf_matches.append((match.start(), match.end(), self._validate_cpf_digit(cpf_digits)))
            detected_positions.update(range(match.start(), match.end()))
        for match in re.finditer(r'\b\d{11}\b', text):
            if any(pos in detected_positions for pos in range(match.start(), match.end())): continue
            if self._has_cpf_context(text, match.start()):
                cpf_matches.append((match.start(), match.end(), self._validate_cpf_digit(match.group())))
        return cpf_matches

    def _is_valid_name(self, name_text: str, full_text: str, is_from_trigger: bool = False) -> bool:
        clean_name = name_text.lower().strip()
        parts = clean_name.split()

        # 1. BLOQUEIO INICIAL (Empresas e Termos Burocráticos)
        if parts[0] in self.INVALID_START_TERMS: return False
        if parts[-1] in self.COMPANY_SUFFIXES: return False
        
        # Bloqueio de termos no meio (ex: "União", "Estados")
        if any(p in self.INVALID_MID_TERMS for p in parts): return False

        if not is_from_trigger and any(p in ['sao', 'santa', 'santo'] for p in parts): return False

        # 2. GATILHO EXPLÍCITO
        if is_from_trigger:
            if len(parts) >= 2 and len(name_text) > 4: return True
            return False

        # 3. REGEX FALLBACK (Exige Âncora)
        has_common_surname = any(p in self.COMMON_SURNAMES for p in parts)
        has_common_first = any(p in self.COMMON_FIRST_NAMES for p in parts)
        
        if not (has_common_surname or has_common_first):
            return False

        if len(parts) < 2: return False
        if len(name_text) < 5: return False

        return True

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int], Dict[str, int]]:
        if pd.isna(text) or not isinstance(text, str):
            return text, {}, {}
        
        indices_to_mask = set()
        protected_indices = set()
        detected_items = [] 
        invalid_cpfs = defaultdict(int)
        detected_names_ranges = set()

        # 1. BLINDAGEM
        for blind_type in ['LEGAL_PROCESS', 'PROTOCOL', 'PROPERTY_REG']:
            for match in re.finditer(self.regex_patterns[blind_type], text):
                protected_indices.update(range(match.start(), match.end()))

        # 2. CPF
        for start, end, is_valid in self._detect_cpf(text):
            if not protected_indices.intersection(range(start, end)):
                indices_to_mask.update(range(start, end))
                detected_items.append((start, end, 'CPF'))
                if not is_valid: invalid_cpfs['CPF_INVALID'] += 1

        # 3. NOMES

        # 3.1 GATILHOS
        trigger_pattern = r'(?i)(?:Nome|Responsável|Interessado|Requerente|Servidor|Paciente|Aluno|Pai|Mãe)[:\s]+([A-Z][a-zÀ-ÿ]+(?:\s+(?:da|de|do|dos|das|e)\s+)?(?:[A-Z][a-zÀ-ÿ]+)+)'
        for match in re.finditer(trigger_pattern, text):
            start_name, end_name = match.span(1)
            name_text = match.group(1)
            if self._is_valid_name(name_text, text, is_from_trigger=True):
                 if not protected_indices.intersection(range(start_name, end_name)):
                    indices_to_mask.update(range(start_name, end_name))
                    detected_names_ranges.update(range(start_name, end_name))
                    detected_items.append((start_name, end_name, 'PERSON_NAME'))

        # 3.2 REGEX FALLBACK
        fallback_pattern = r'\b([A-Z][a-zçáéíóúãõâêô]+(?:\s(?:da|de|do|dos|das|e)\s|\s)[A-Z][a-zçáéíóúãõâêô]+(?:(?:\s(?:da|de|do|dos|das|e)\s|\s)[A-Z][a-zçáéíóúãõâêô]+)*)\b'
        
        for match in re.finditer(fallback_pattern, text):
            start, end = match.span()
            name_text = match.group(1)
            if set(range(start, end)).intersection(detected_names_ranges): continue
            
            # Context Lookback (Antes do nome)
            lookback_window = text[max(0, start-30):start].lower()
            last_tokens = [t for t in re.split(r'[\s:;.,-]+', lookback_window) if t][-3:]
            if any(token in self.CONTEXT_BLOCKERS for token in last_tokens):
                continue
            
            # Context Lookahead (Depois do nome)
            lookahead_window = text[end:min(len(text), end+20)].lower()
            next_tokens = [t for t in re.split(r'[\s:;.,-]+', lookahead_window) if t][:2]
            if any(token in self.COMPANY_SUFFIXES for token in next_tokens):
                continue

            if self._is_valid_name(name_text, text, is_from_trigger=False):
                if not protected_indices.intersection(range(start, end)):
                    indices_to_mask.update(range(start, end))
                    detected_names_ranges.update(range(start, end))
                    detected_items.append((start, end, 'PERSON_NAME'))

        # 4. OUTROS
        other_patterns = ['MATRICULA', 'INSCRICAO', 'RG', 'CNH', 'CNPJ', 'CEP', 'EMAIL', 'FULL_ADDRESS', 'PHONE']
        for p_type in other_patterns:
            if p_type not in self.regex_patterns and p_type != 'PHONE': continue 
            if p_type == 'PHONE': continue 
            
            pat = self.regex_patterns[p_type]
            for match in re.finditer(pat, text):
                start, end = match.span(1) if match.groups() else match.span()
                if p_type == 'FULL_ADDRESS':
                    if any(bad in match.group().lower() for bad in self.INVALID_START_TERMS): continue

                if not protected_indices.intersection(range(start, end)) and \
                   not set(range(start, end)).intersection(indices_to_mask):
                    indices_to_mask.update(range(start, end))
                    detected_items.append((start, end, p_type))

        # 5. TELEFONE E SENSÍVEIS
        phone_pats = [
            r'\b(?:\(?\s*0?([1-9][0-9])\s*\)?\s?)?(?:9\s?\d{4}[-.\s]?\d{4}|\d{4}[-.\s]?\d{4})\b',
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,15}\b'
        ]
        for pat in phone_pats:
            for match in re.finditer(pat, text):
                start, end = match.span()
                if re.search(r'(?:19|20)\d{2}$', match.group().strip()): continue
                prefix = text[max(0, start-1):start]
                if prefix in ['/', '-']: continue
                if not protected_indices.intersection(range(start, end)) and \
                   not set(range(start, end)).intersection(indices_to_mask):
                    indices_to_mask.update(range(start, end))
                    detected_items.append((start, end, 'PHONE'))
                    
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    if not protected_indices.intersection(range(match.start(), match.end())):
                        indices_to_mask.update(range(match.start(), match.end()))
                        detected_items.append((match.start(), match.end(), sens_type))

        # 6. MESCLAGEM
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

# ... (Manter Logger, generate_report e main igual ao anterior) ...


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