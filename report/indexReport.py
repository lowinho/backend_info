"""
Processador Standalone de PII com Relatório Estruturado
Versão simplificada que apenas processa e exibe relatórios sem salvar em banco
"""
import pandas as pd
import spacy
import re
import os
import time
from datetime import datetime
from collections import defaultdict

# --- Configuration ---
FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
TARGET_COLUMN = 'Texto Mascarado'


class PIIDetector:
    """Detector de PII (Personal Identifiable Information)"""
    
    # Tipos de PII e suas descrições
    PII_DESCRIPTIONS = {
        'CPF': 'Cadastro de Pessoa Física',
        'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
        'RG': 'Registro Geral',
        'EMAIL': 'Endereço de E-mail',
        'PHONE': 'Número de Telefone',
        'CEP': 'Código de Endereçamento Postal',
        'SEI_PROCESS': 'Número de Processo SEI',
        'PERSON_NAME': 'Nome de Pessoa',
        'LOCATION': 'Localização/Endereço',
        'DATE_BIRTH': 'Data de Nascimento'
    }
    
    def __init__(self):
        print("=" * 80)
        print("🤖 INICIALIZANDO DETECTOR DE PII")
        print("=" * 80)
        
        try:
            print("📦 Carregando modelo de NLP português...")
            self.nlp = spacy.load("pt_core_news_lg")
            print("✅ Modelo carregado com sucesso!")
        except OSError:
            print("❌ ERRO: Modelo não encontrado.")
            print("   Execute: python -m spacy download pt_core_news_lg")
            exit(1)
        
        # Padrões Regex para dados estruturados
        self.regex_patterns = {
            'CPF': r'\b\d{3}\.?\d{3}\.?\d{3}[-\s]?\d{2}\b',
            'CNPJ': r'\b\d{2}\.?\d{3}\.?\d{3}[/]?\d{4}[-\s]?\d{2}\b',
            'RG': r'\b\d{1,2}\.?\d{3}\.?\d{3}[-\s]?[0-9xX]\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}|\d{4})[-.\s]?\d{4}\b',
            'CEP': r'\b\d{5}[-\s]?\d{3}\b',
            'SEI_PROCESS': r'\b\d{5}[-\s]?\d{6,}[/]?\d{4}[-\s]?\d{2}\b',
            'DATE_BIRTH': r'\b(?:0?[1-9]|[12][0-9]|3[01])[/\-](?:0?[1-9]|1[0-2])[/\-](?:19|20)\d{2}\b'
        }
        
        print(f"🔍 {len(self.regex_patterns)} tipos de PII configurados para detecção")
        print()

    def detect_and_redact(self, text):
        """
        Detecta e anonimiza PII no texto
        
        Returns:
            tuple: (texto_anonimizado, estatísticas_pii)
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
        
        # 2. Detecção via NLP (nomes e localizações)
        doc = self.nlp(text)
        for ent in doc.ents:
            # Nomes de pessoas (mínimo 2 palavras)
            if ent.label_ == "PER" and len(ent.text.split()) > 1:
                pii_stats['PERSON_NAME'] += 1
                indices_to_mask.update(range(ent.start_char, ent.end_char))
            # Localizações
            elif ent.label_ == "LOC":
                pii_stats['LOCATION'] += 1
                indices_to_mask.update(range(ent.start_char, ent.end_char))
        
        # 3. Aplicar máscara
        redacted_chars = []
        for i, char in enumerate(text):
            if i in indices_to_mask and char.isalnum():
                redacted_chars.append('x')
            else:
                redacted_chars.append(char)
        
        return "".join(redacted_chars), dict(pii_stats)


class ReportGenerator:
    """Gerador de relatórios estruturados"""
    
    @staticmethod
    def print_header(title):
        """Imprime cabeçalho formatado"""
        print()
        print("=" * 80)
        print(f"  {title}")
        print("=" * 80)
        print()
    
    @staticmethod
    def print_section(title):
        """Imprime seção formatada"""
        print()
        print("─" * 80)
        print(f"📊 {title}")
        print("─" * 80)
    
    @staticmethod
    def calculate_risk_level(pii_stats, total_records):
        """Calcula nível de risco LGPD"""
        critical_pii = {'CPF', 'CNPJ', 'RG'}
        high_risk_pii = {'EMAIL', 'PHONE', 'DATE_BIRTH'}
        
        critical_count = sum(pii_stats.get(pii, 0) for pii in critical_pii)
        high_count = sum(pii_stats.get(pii, 0) for pii in high_risk_pii)
        total_pii = sum(pii_stats.values())
        
        if critical_count > 0:
            if critical_count / total_records > 0.5:
                return '🔴 CRÍTICO'
            return '🟠 ALTO'
        elif high_count > 0:
            return '🟡 MÉDIO'
        elif total_pii > 0:
            return '🟢 BAIXO'
        else:
            return '⚪ MÍNIMO'
    
    @staticmethod
    def print_summary_table(pii_breakdown, detector):
        """Imprime tabela de resumo de PII"""
        if not pii_breakdown:
            print("   Nenhum dado sensível detectado.")
            return
        
        # Cabeçalho
        print(f"{'TIPO':<20} {'DESCRIÇÃO':<35} {'QUANTIDADE':>12} {'%':>8}")
        print("-" * 80)
        
        # Ordenar por quantidade (maior primeiro)
        total = sum(pii_breakdown.values())
        sorted_pii = sorted(pii_breakdown.items(), key=lambda x: x[1], reverse=True)
        
        # Linhas
        for pii_type, count in sorted_pii:
            description = detector.PII_DESCRIPTIONS.get(pii_type, pii_type)
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{pii_type:<20} {description:<35} {count:>12,} {percentage:>7.1f}%")
        
        # Total
        print("-" * 80)
        print(f"{'TOTAL':<20} {'':<35} {total:>12,} {'100.0%':>8}")


def main():
    """Função principal"""
    
    # ==========================================
    # 1. VALIDAÇÃO DO ARQUIVO
    # ==========================================
    ReportGenerator.print_header("VALIDAÇÃO DO ARQUIVO")
    
    print(f"📁 Arquivo: {FILE_NAME}")
    
    if not os.path.exists(FILE_NAME):
        print(f"❌ ERRO: Arquivo '{FILE_NAME}' não encontrado.")
        exit(1)
    
    file_size = os.path.getsize(FILE_NAME) / (1024 * 1024)  # MB
    print(f"📏 Tamanho: {file_size:.2f} MB")
    print("✅ Arquivo encontrado!")
    
    # ==========================================
    # 2. LEITURA DO ARQUIVO
    # ==========================================
    ReportGenerator.print_header("LEITURA DOS DADOS")
    
    print("📖 Lendo arquivo Excel...")
    try:
        df = pd.read_excel(FILE_NAME)
        print(f"✅ Arquivo carregado: {len(df)} registros, {len(df.columns)} colunas")
    except Exception as e:
        print(f"❌ ERRO ao ler arquivo: {e}")
        exit(1)
    
    print(f"\n📋 Colunas encontradas:")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i}. {col}")
    
    if TARGET_COLUMN not in df.columns:
        print(f"\n❌ ERRO: Coluna '{TARGET_COLUMN}' não encontrada.")
        exit(1)
    
    print(f"\n✅ Coluna alvo identificada: '{TARGET_COLUMN}'")
    
    # ==========================================
    # 3. INICIALIZAÇÃO DO DETECTOR
    # ==========================================
    detector = PIIDetector()
    
    # ==========================================
    # 4. PROCESSAMENTO
    # ==========================================
    ReportGenerator.print_header("PROCESSAMENTO DE DADOS")
    
    print(f"🔄 Processando {len(df)} registros...")
    print()
    
    start_time = time.time()
    
    # Processar cada registro
    anonymized_texts = []
    pii_stats_total = defaultdict(int)
    records_with_pii = 0
    
    # Barra de progresso simples
    total = len(df)
    for idx, row in df.iterrows():
        # Progresso
        if (idx + 1) % 100 == 0 or idx == 0:
            progress = (idx + 1) / total * 100
            print(f"   Progresso: {idx + 1}/{total} ({progress:.1f}%)", end='\r')
        
        original_text = row[TARGET_COLUMN]
        anonymized_text, pii_stats = detector.detect_and_redact(original_text)
        
        anonymized_texts.append(anonymized_text)
        
        # Acumular estatísticas
        if pii_stats:
            records_with_pii += 1
            for pii_type, count in pii_stats.items():
                pii_stats_total[pii_type] += count
    
    print()  # Nova linha após progresso
    
    # Adicionar coluna anonimizada
    df['Texto_Anonimizado'] = anonymized_texts
    df['Data_Processamento'] = datetime.now()
    
    processing_time = time.time() - start_time
    
    print()
    print(f"✅ Processamento concluído em {processing_time:.2f} segundos")
    print(f"⚡ Velocidade: {len(df)/processing_time:.1f} registros/segundo")
    
    # ==========================================
    # 5. RELATÓRIO FINAL
    # ==========================================
    ReportGenerator.print_header("RELATÓRIO DE PROCESSAMENTO")
    
    # Informações gerais
    ReportGenerator.print_section("Informações Gerais")
    print(f"   📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"   📁 Arquivo: {os.path.basename(FILE_NAME)}")
    print(f"   📊 Total de Registros: {len(df):,}")
    print(f"   ⏱️  Tempo de Processamento: {processing_time:.2f}s")
    print(f"   ⚡ Velocidade: {len(df)/processing_time:.1f} registros/s")
    
    # Estatísticas de PII
    ReportGenerator.print_section("Estatísticas de PII Detectado")
    total_pii = sum(pii_stats_total.values())
    pii_rate = (records_with_pii / len(df) * 100) if len(df) > 0 else 0
    
    print(f"   🔍 Total de PII Detectado: {total_pii:,}")
    print(f"   📝 Registros com PII: {records_with_pii:,} ({pii_rate:.1f}%)")
    print(f"   📝 Registros sem PII: {len(df) - records_with_pii:,} ({100-pii_rate:.1f}%)")
    print()
    
    # Tabela detalhada
    ReportGenerator.print_summary_table(dict(pii_stats_total), detector)
    
    # Análise de Risco
    ReportGenerator.print_section("Análise de Risco LGPD")
    risk_level = ReportGenerator.calculate_risk_level(dict(pii_stats_total), len(df))
    print(f"   Nível de Risco: {risk_level}")
    print()
    
    # Recomendações baseadas no risco
    print("   📋 Recomendações:")
    
    if 'CPF' in pii_stats_total or 'RG' in pii_stats_total:
        print("      • Documentos de identificação detectados - implementar pseudonimização")
    
    if 'EMAIL' in pii_stats_total or 'PHONE' in pii_stats_total:
        print("      • Dados de contato detectados - obter consentimento explícito")
    
    if risk_level.startswith('🔴') or risk_level.startswith('🟠'):
        print("      • Implementar criptografia adicional para armazenamento")
        print("      • Restringir acesso apenas a usuários autorizados")
        print("      • Implementar log de auditoria para acessos")
    else:
        print("      • Manter boas práticas de segurança da informação")
    
    # Exemplos de anonimização
    ReportGenerator.print_section("Exemplos de Anonimização")
    
    # Pegar até 3 exemplos de registros com PII
    examples_shown = 0
    for idx, row in df.iterrows():
        if examples_shown >= 3:
            break
        
        original = str(row[TARGET_COLUMN])
        anonymized = str(row['Texto_Anonimizado'])
        
        # Verificar se há diferença (PII foi detectado)
        if original != anonymized and len(original) < 200:
            examples_shown += 1
            print(f"\n   Exemplo {examples_shown}:")
            print(f"   ORIGINAL   : {original[:100]}...")
            print(f"   ANONIMIZADO: {anonymized[:100]}...")
    
    if examples_shown == 0:
        print("   (Nenhum exemplo disponível - registros muito longos ou sem PII)")
    
    # ==========================================
    # 6. FINALIZAÇÃO
    # ==========================================
    ReportGenerator.print_header("PROCESSO FINALIZADO")
    
    print("✅ Todos os dados foram processados com sucesso!")
    print()
    print("📊 Resumo:")
    print(f"   • Registros processados: {len(df):,}")
    print(f"   • PII detectado: {total_pii:,} ocorrências")
    print(f"   • Tipos de PII: {len(pii_stats_total)}")
    print(f"   • Tempo total: {processing_time:.2f}s")
    print()
    print("💾 Para salvar os resultados, o DataFrame 'df' contém:")
    print("   • Coluna 'Texto_Anonimizado': Textos processados")
    print("   • Coluna 'Data_Processamento': Timestamp do processamento")
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário.")
        exit(0)
    except Exception as e:
        print(f"\n\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)