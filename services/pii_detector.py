import spacy
import re
import phonenumbers
import pandas as pd
from collections import defaultdict
from typing import Tuple, Dict, List

class PIIDetector:
    """
    Detector de PII V15.4 (Backend Service)
    Sincronizado com Script Standalone V15.4
    - Rollback Lógica de Nomes (V15.2)
    - Validação ANATEL para Telefones
    - Expansão de Endereços (SHDF/Lotes)
    """
    
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

    # --- VALIDAÇÃO DE CPF ---
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
            if self._is_blocked_by_nis(text, match.start(), match.end()): continue
            if self._has_cpf_context(text, match.start()):
                cpf_matches.append((match.start(), match.end(), self._validate_cpf_digit(match.group())))
        return cpf_matches

    # --- VALIDAÇÃO DE TELEFONE (ANATEL) ---
    def _is_valid_phone_structure(self, phone_text: str) -> bool:
        digits = re.sub(r'\D', '', phone_text)
        if len(digits) not in [10, 11]: return False 
        try:
            ddd = int(digits[:2])
            first_num = int(digits[2])
            if ddd not in self.VALID_DDDS: return False
            if len(digits) == 11: 
                if first_num != 9: return False # Celular
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

        # 2. CPF (Com lógica anti-NIS)
        for start, end, is_valid in self._detect_cpf(text):
            if not protected_indices.intersection(range(start, end)):
                indices_to_mask.update(range(start, end))
                detected_items.append((start, end, 'CPF'))
                if not is_valid: invalid_cpfs['CPF_INVALID'] += 1

        # 3. Nomes (Gatilhos - V15.2 Lógica)
        trigger_pattern = r'(?i:(?:Nome|Responsável|Interessado|Requerente|Servidor|Paciente|Aluno|Pai|Mãe|Me chamo|Sou|Eu\,|Att\.?|Atenciosamente|Procurador|Representante|Advogado))[:\s,]+([A-Z][a-zÀ-ÿ]+(?:\s+(?:da|de|do|dos|das|e)\s+)?(?:[A-Z][a-zÀ-ÿ]+)*)'
        
        for match in re.finditer(trigger_pattern, text):
            if not match.group(1): continue
            start_name, end_name = match.span(1)
            name_text = match.group(1)
            
            is_valid = False
            parts = name_text.split()
            
            if len(parts) >= 2:
                is_valid = self.validar_nome_pessoa(name_text)
            elif len(parts) == 1 and name_text.lower() in self.COMMON_FIRST_NAMES:
                trigger_word = text[match.start():start_name].lower()
                if any(w in trigger_word for w in ['sou', 'chamo', 'eu']): 
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
                
                # Contexto Negativo
                lookback = text[max(0, start-40):start].lower()
                if any(t in lookback for t in ['nire', 'protocolo', 'processo', 'sei', 'lai', 'cda', 'certidao', 'divida', 'gerador', 'ac']):
                    continue
                
                # Validação Lógica
                phone_candidate = match.group()
                digits = re.sub(r'\D', '', phone_candidate)
                if len(digits) >= 10 and not self._is_valid_phone_structure(digits):
                    continue

                if not protected_indices.intersection(range(start, end)) and \
                   not set(range(start, end)).intersection(indices_to_mask):
                    indices_to_mask.update(range(start, end))
                    detected_items.append((start, end, 'PHONE'))
                    
        # 7. Dados Sensíveis
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    # Exceção Gênero V15.4
                    if sens_type == 'SENSITIVE_GENDER':
                         snippet = text[max(0, match.start()-60):min(len(text), match.end()+60)].lower()
                         if any(t in snippet for t in ['lei', 'decreto', 'artigo', 'dispõe', 'preencher', 'campo', 'caso possua', 'informar', 'se houver', 'uso do nome social']):
                             continue
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