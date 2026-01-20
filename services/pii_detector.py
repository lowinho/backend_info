"""
Serviço de detecção e anonimização de informações pessoais (PII)
"""
import pandas as pd
import spacy
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class PIIDetector:
    """
    Detector avançado de PII (Personal Identifiable Information) para compliance LGPD
    """
    
    # Tipos de PII detectados
    PII_TYPES = {
        'CPF': 'Cadastro de Pessoa Física',
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'RG': 'Registro Geral',
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Telefone',
        'CEP': 'Código de Endereçamento Postal',
        'CREDIT_CARD': 'Cartão de Crédito',
        'SEI_PROCESS': 'Processo SEI',
        'PERSON_NAME': 'Nome de Pessoa',
        'LOCATION': 'Localização',
        'DATE_BIRTH': 'Data de Nascimento'
    }
    
    def __init__(self):
        """Inicializa o detector com modelo NLP e padrões regex"""
        print("🔍 Inicializando detector de PII...")
        
        try:
            self.nlp = spacy.load("pt_core_news_lg")
            print("✅ Modelo NLP carregado: pt_core_news_lg")
        except OSError:
            print("❌ Modelo não encontrado. Execute: python -m spacy download pt_core_news_lg")
            raise
        
        # Padrões regex para detecção
        self.regex_patterns = {
            'CPF': r'\b\d{3}\.?\d{3}\.?\d{3}[-\s]?\d{2}\b',
            'CNPJ': r'\b\d{2}\.?\d{3}\.?\d{3}[/]?\d{4}[-\s]?\d{2}\b',
            'RG': r'\b\d{1,2}\.?\d{3}\.?\d{3}[-\s]?[0-9xX]\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}|\d{4})[-.\s]?\d{4}\b',
            'CEP': r'\b\d{5}[-\s]?\d{3}\b',
            'CREDIT_CARD': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'SEI_PROCESS': r'\b\d{5}[-\s]?\d{6,}[/]?\d{4}[-\s]?\d{2}\b',
            'DATE_BIRTH': r'\b(?:0?[1-9]|[12][0-9]|3[01])[/\-](?:0?[1-9]|1[0-2])[/\-](?:19|20)\d{2}\b'
        }
        
    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Detecta e anonimiza PII no texto
        
        Args:
            text: Texto original a ser processado
            
        Returns:
            Tuple com (texto_anonimizado, estatísticas_de_detecção)
        """
        if pd.isna(text) or not isinstance(text, str):
            return text, {}
        
        indices_to_mask = set()
        pii_stats = defaultdict(int)
        
        # 1. Detecção via Regex (dados estruturados)
        for pii_type, pattern in self.regex_patterns.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                pii_stats[pii_type] += len(matches)
                for match in matches:
                    indices_to_mask.update(range(match.start(), match.end()))
        
        # 2. Detecção via NLP (nomes de pessoas e localizações)
        doc = self.nlp(text)
        for ent in doc.ents:
            # Nomes de pessoas (2+ palavras para evitar falsos positivos)
            if ent.label_ == "PER" and len(ent.text.split()) > 1:
                pii_stats['PERSON_NAME'] += 1
                indices_to_mask.update(range(ent.start_char, ent.end_char))
            
            # Localizações (endereços)
            elif ent.label_ == "LOC":
                pii_stats['LOCATION'] += 1
                indices_to_mask.update(range(ent.start_char, ent.end_char))
        
        # 3. Aplicar máscara (substituir alfanuméricos por 'x')
        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask and char.isalnum():
                redacted_chars.append('x')
            else:
                redacted_chars.append(char)
        
        redacted_text = "".join(redacted_chars)
        
        return redacted_text, dict(pii_stats)
    
    def analyze_text(self, text: str) -> Dict[str, any]:
        """
        Analisa texto sem anonimizar (apenas para estatísticas)
        
        Args:
            text: Texto a ser analisado
            
        Returns:
            Dicionário com estatísticas detalhadas
        """
        if pd.isna(text) or not isinstance(text, str):
            return {
                'total_pii': 0,
                'pii_types': {},
                'has_pii': False
            }
        
        pii_stats = defaultdict(int)
        
        # Detecção via Regex
        for pii_type, pattern in self.regex_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                pii_stats[pii_type] = len(matches)
        
        # Detecção via NLP
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PER" and len(ent.text.split()) > 1:
                pii_stats['PERSON_NAME'] += 1
            elif ent.label_ == "LOC":
                pii_stats['LOCATION'] += 1
        
        total_pii = sum(pii_stats.values())
        
        return {
            'total_pii': total_pii,
            'pii_types': dict(pii_stats),
            'has_pii': total_pii > 0
        }
    
    def get_pii_type_description(self, pii_type: str) -> str:
        """Retorna descrição legível do tipo de PII"""
        return self.PII_TYPES.get(pii_type, pii_type)