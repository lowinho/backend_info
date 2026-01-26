"""
Processador Standalone de PII - V9.0 (Telefones Blindados + Registros Gerais)
Melhorias:
- Regex de telefone estrito para evitar confusão com processos.
- Nova categoria 'Registros Gerais' (RG, NIS, PIS, CNH, etc).
"""
import pandas as pd
import spacy
import re
import os
import time
import phonenumbers
from collections import defaultdict
from typing import Dict, Tuple

# --- Configuração ---
# FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
FILE_NAME = './files/amostra_validacao_lgpd_v2.csv'
TARGET_COLUMN = 'Texto Mascarado'

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    GREY = '\033[90m'

class PIIDetector:
    """
    Detector de PII V9.0
    """
    
    PII_TYPES = {
        'PERSON_NAME': 'Nome de Pessoa',
        'CPF': 'Cadastro de Pessoa Física',
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Número de Telefone',
        'FULL_ADDRESS': 'Endereço Completo',
        'GENERAL_REGISTRY': 'Registros Gerais (RG/NIS/PIS/CNH)', # Nova Categoria
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

    def __init__(self):
        print("📦 Carregando recursos de IA (PIIDetector V9.0)...", end='\r')
        try:
            self.nlp = spacy.load("pt_core_news_lg")
            pipes_to_disable = ['parser', 'tagger', 'morphologizer', 'lemmatizer']
            existing_pipes = [p for p in pipes_to_disable if p in self.nlp.pipe_names]
            if existing_pipes:
                self.nlp.disable_pipes(existing_pipes)
        except OSError:
            print(f"{Colors.FAIL}Erro: Modelo 'pt_core_news_lg' não encontrado.{Colors.ENDC}")
            self.nlp = None

        # --- REGEX OTIMIZADO (Blindado contra Processos) ---
        self.phone_patterns = [
            # 1. Formatado (Ex: (61) 91234-5678)
            # Regra: DDD deve ser [1-9]{2}. O primeiro dígito do número deve ser 9 (celular) ou 2-5 (fixo).
            # Isso elimina "01235" (começa com 0) e números aleatórios.
            r'\b(?:\(?[1-9]{2}\)?\s?)(?:9\s?\d|[2-5]\d)\d{2}[-.\s]\d{4}\b',
            
            # 2. Celular Solto (Ex: 61988887777)
            # Regra: DDD[1-9]{2} + 9 + 8 dígitos. Total 11 dígitos exatos.
            r'\b[1-9]{2}9\d{8}\b',
            
            # 3. Fixo Solto (Ex: 1133334444)
            # Regra: DDD[1-9]{2} + [2-5] + 7 dígitos. Total 10 dígitos exatos.
            r'\b[1-9]{2}[2-5]\d{7}\b',

            # 4. Contexto Explícito (Backup)
            # Só aceita formato livre se tiver a palavra mágica antes
            r'(?i)(?:tel|cel|zap|whatsapp|contato|fone)[:\s\.]+\d{8,12}\b'
        ]

        self.regex_patterns = {
            'CPF': r'(?:\b\d{3}\.\d{3}\.\d{3}-\d{2}\b)|(?<=CPF[:\s])\s*\d{11}',
            'CNPJ': r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\.br)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'FULL_ADDRESS': r'(?i)\b(?:Rua|Av\.|Avenida|Q\.|Qd\.|Quadra|SQN|SQS|SHN|SHS|CLN|CRN|SRES|SHDF|Cond\.|Bloco|Bl\.|Lote|Lt\.|Conjunto|Conj\.)\s+[A-Za-z0-9\s,.-]{1,100}(?:(?:\b\d+|[A-Z]\b))',
            
            # REGISTROS GERAIS (Unificado)
            # Captura: RG, CNH, NIS, PIS, PASEP, Título de Eleitor, CTPS
            # Padrões:
            # - Contexto explícito (RG: 1234)
            # - Formato NIS/PIS (000.00000.00-0)
            'GENERAL_REGISTRY': r'(?i)(?:RG|CNH|Matr[íi]cula|NIS|PIS|PASEP|NIT|CTPS|T[íi]tulo\s(?:de\s)?Eleitor)[:\s\.]+\d{1,15}[-\d]*|\b\d{3}\.\d{5}\.\d{2}-\d\b'
        }

        self.sensitive_keywords = {
            'SENSITIVE_HEALTH': [r'\bc[âa]ncer\b', r'\boncologia\b', r'\bhiv\b', r'\baids\b', r'\basm[áa]tico\b', r'\bminha doen[çc]a\b', r'\blaudo m[ée]dico\b', r'\bCID\s?[A-Z]\d', r'\btranstorno\b', r'\bdepress[ãa]o\b', r'\bdefici[êe]ncia\b', r'\bautis'],
            'SENSITIVE_MINOR': [r'\bmenor de idade\b', r'\bcrian[çc]a\b', r'\bfilh[ao] (?:de )?menor\b', r'\btutela\b', r'\bcreche\b', r'\balun[ao]\b'],
            'SENSITIVE_SOCIAL': [r'\bvulnerabilidade\b', r'\baux[íi]lio emergencial\b', r'\bcesta b[áa]sica\b', r'\bbolsa fam[íi]lia\b'],
            'SENSITIVE_RACE': [r'\bcor d[ae] pele\b', r'\braça\b', r'\betnia\b', r'\bnegro\b', r'\bpardo\b'],
            'SENSITIVE_GENDER': [r'\btrans\b', r'\bhormoniza[çc][ãa]o\b', r'\bidentidade de g[êe]nero\b']
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

        # 2. Telefones (Regex Estrito + Google Lib)
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text):
                match_range = set(range(match.start(), match.end()))
                if not match_range.intersection(indices_to_mask):
                    indices_to_mask.update(match_range)
                    pii_stats['PHONE'] += 1
        
        # Backup com Phonenumbers
        try:
            for match in phonenumbers.PhoneNumberMatcher(text, "BR"):
                if phonenumbers.is_valid_number(match.number):
                    match_range = set(range(match.start, match.end))
                    # Validação extra: Se o regex estrito já pegou, ignoramos para não duplicar
                    if not match_range.intersection(indices_to_mask):
                        indices_to_mask.update(match_range)
                        pii_stats['PHONE'] += 1
        except Exception:
            pass

        # 3. Sensíveis
        for sens_type, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    indices_to_mask.update(range(match.start(), match.end()))
                    pii_stats[sens_type] += 1

        # 4. Nomes (NLP + IBGE)
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == "PER":
                        name_candidate = ent.text.strip()
                        clean_name = re.sub(r'[^\w\s]', '', name_candidate.lower())
                        parts = clean_name.split()
                        
                        if len(parts) < 2: continue
                        
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

        # 5. Anonimização
        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask:
                redacted_chars.append('x' if char.isalnum() else char)
            else:
                redacted_chars.append(char)
        
        return "".join(redacted_chars), dict(pii_stats)

    def get_description(self, key):
        return self.PII_TYPES.get(key, key)


class DashboardGenerator:
    @staticmethod
    def print_dashboard(df, pii_details, records_with_pii, processing_time, detector):
        total_records = len(df)
        pii_rate = (records_with_pii / total_records * 100) if total_records > 0 else 0
        
        pii_stats_total = {k: sum(item['qtd'] for item in v) for k, v in pii_details.items()}
        
        risk_color = Colors.GREEN
        risk_label = "BAIXO"
        risk_desc = "Poucos dados pessoais esparsos."
        
        sensitive_keys = ['SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 'SENSITIVE_RACE', 'SENSITIVE_GENDER']
        has_sensitive = any(k in pii_stats_total for k in sensitive_keys)
        has_mass_ids = sum(pii_stats_total.get(k, 0) for k in ['CPF', 'CNPJ', 'GENERAL_REGISTRY']) > (total_records * 0.1)
        
        if has_sensitive or has_mass_ids:
            risk_color = Colors.FAIL
            risk_label = "CRÍTICO"
            risk_desc = "Dados sensíveis ou identificadores oficiais em massa."
        elif records_with_pii > 0:
            risk_color = Colors.WARNING
            risk_label = "ALTO"
            risk_desc = "Identificadores pessoais detectados."

        print("\n" * 2)
        print(f"{Colors.BOLD}🔵 Relatório de Classificação de Pedido (LGPD){Colors.ENDC}")
        print(f"{Colors.CYAN}   Arquivo analisado: {os.path.basename(FILE_NAME)}{Colors.ENDC}")
        print()
        
        print(f"{risk_color}{'='*80}{Colors.ENDC}")
        print(f"{risk_color} ⚠  CLASSIFICAÇÃO: PEDIDO NÃO PÚBLICO ({risk_label}){Colors.ENDC}")
        print(f"    {risk_desc}")
        print(f"{risk_color}{'='*80}{Colors.ENDC}")
        print()

        print(f"{Colors.BOLD}INDICADORES DO PROCESSAMENTO{Colors.ENDC}")
        print("-" * 40)
        metrics = [
            ("Registros analisados", f"{total_records}"),
            ("Com dados sensíveis", f"{records_with_pii}", Colors.FAIL if records_with_pii > 0 else Colors.GREEN),
            ("Sem dados sensíveis", f"{total_records - records_with_pii}"),
            ("Taxa de incidência", f"{pii_rate:.1f}%"),
            ("Tempo processamento", f"{processing_time:.2f}s")
        ]
        
        for label, val, *color_opt in metrics:
            color = color_opt[0] if color_opt else Colors.ENDC
            print(f"{label:<25} {color}{val:>5}{Colors.ENDC}")
        print()

        print(f"{Colors.BOLD}DETALHAMENTO POR TIPO DE DADO E REGISTRO{Colors.ENDC}")
        print("-" * 80)
        
        sorted_details = sorted(pii_details.items(), key=lambda x: sum(i['qtd'] for i in x[1]), reverse=True)
        
        for pii_type, occurrences in sorted_details:
            total_count = sum(item['qtd'] for item in occurrences)
            desc = detector.get_description(pii_type)
            
            color_badge = Colors.FAIL if "Sensível" in desc or pii_type in ['CPF', 'CNPJ', 'GENERAL_REGISTRY'] else Colors.WARNING
            print(f"{color_badge}[{desc}: {total_count} ocorrências]{Colors.ENDC}")
            
            ids_str_list = [f"ID {item['id']} (Qtd: {item['qtd']})" for item in occurrences]
            details_str = ", ".join(ids_str_list)
            
            print(f"{Colors.GREY}   └── Ocorreu nos registros: {details_str}{Colors.ENDC}")
            print() 


def main():
    if not os.path.exists(FILE_NAME):
        print(f"Arquivo '{FILE_NAME}' não encontrado.")
        return

    detector = PIIDetector()
    
    try:
        if FILE_NAME.endswith('.csv'):
            df = pd.read_csv(FILE_NAME)
        else:
            df = pd.read_excel(FILE_NAME)
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return

    df.columns = [c.strip() for c in df.columns]
    
    target_col = next((c for c in df.columns if TARGET_COLUMN.lower() in c.lower()), None)
    if not target_col:
        for col in df.columns:
            if df[col].dtype == 'object' and df[col].str.len().mean() > 20:
                target_col = col
                break
    
    if not target_col:
        print(f"Coluna de texto não identificada.")
        return

    possible_id_cols = ['id', 'ID', 'Id', 'Protocolo', 'protocolo']
    id_col = next((col for col in possible_id_cols if col in df.columns), None)

    print(f"Processando {len(df)} registros na coluna '{target_col}'...", end=' ')
    start_time = time.time()
    
    pii_details = defaultdict(list)
    records_with_pii = 0

    for idx, row in df.iterrows():
        text_content = str(row[target_col])
        _, stats = detector.detect_and_redact(text_content)
        
        if stats:
            records_with_pii += 1
            record_id = row[id_col] if id_col else f"Linha_{idx + 2}"
            
            for pii_type, count in stats.items():
                pii_details[pii_type].append({'id': record_id, 'qtd': count})
    
    processing_time = time.time() - start_time
    print("Concluído! ✅")

    DashboardGenerator.print_dashboard(df, pii_details, records_with_pii, processing_time, detector)

if __name__ == "__main__":
    main()