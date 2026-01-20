#!/usr/bin/env python
"""
Script standalone para processar arquivos localmente
(mantém compatibilidade com o código original)

Uso:
    python process_file.py --file dados.csv
    python process_file.py --file dados.txt
"""

import argparse
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from services.pii_detector import PIIDetector
from services.file_processor import FileProcessor
from services.report_service import ReportService
from database.mongo_service import MongoService
from config import Config
import uuid


def main():
    parser = argparse.ArgumentParser(
        description='Processa arquivo CSV ou TXT detectando e anonimizando PII'
    )
    parser.add_argument(
        '--file',
        type=str,
        required=True,
        help='Caminho do arquivo CSV ou TXT a ser processado'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Não salvar no MongoDB (apenas processar)'
    )
    
    args = parser.parse_args()
    
    # Validar arquivo
    if not os.path.exists(args.file):
        print(f"❌ Erro: Arquivo '{args.file}' não encontrado.")
        sys.exit(1)
    
    file_ext = args.file.rsplit('.', 1)[-1].lower()
    if file_ext not in ['csv', 'txt']:
        print(f"❌ Erro: Extensão '{file_ext}' não suportada. Use CSV ou TXT.")
        sys.exit(1)
    
    print("=" * 60)
    print("🔒 Processador de Dados Pessoais (LGPD)")
    print("=" * 60)
    print(f"📄 Arquivo: {args.file}")
    print(f"📊 Tipo: {file_ext.upper()}")
    print("=" * 60)
    
    # Inicializar serviços
    detector = PIIDetector()
    processor = FileProcessor(detector)
    
    # Gerar UUID para o processamento
    process_uuid = str(uuid.uuid4())
    print(f"🔑 UUID do Processamento: {process_uuid}")
    print()
    
    # Processar arquivo
    try:
        if file_ext == 'csv':
            result = processor.process_csv(args.file, process_uuid)
        else:
            result = processor.process_txt(args.file, process_uuid)
        
        # Exibir estatísticas
        print()
        print("=" * 60)
        print("📊 RESULTADOS DO PROCESSAMENTO")
        print("=" * 60)
        print(f"Total de registros: {result['total_records']}")
        print(f"Registros com PII: {result['records_with_pii']}")
        print(f"Tempo de processamento: {result['processing_time']:.2f}s")
        print()
        print("PII Detectado:")
        for pii_type, count in sorted(result['pii_stats'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {pii_type}: {count}")
        
        # Gerar relatório
        report_service = ReportService()
        report = report_service.create_report(
            process_uuid=process_uuid,
            filename=os.path.basename(args.file),
            file_type=file_ext,
            total_records=result['total_records'],
            pii_statistics=result['pii_stats'],
            processing_time=result['processing_time']
        )
        
        print()
        print("=" * 60)
        print("⚠️  ANÁLISE DE RISCO LGPD")
        print("=" * 60)
        print(f"Nível: {report['risk_assessment']['level']}")
        print(f"Descrição: {report['risk_assessment']['description']}")
        print()
        print("Recomendações:")
        for i, rec in enumerate(report['risk_assessment']['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        # Salvar no MongoDB
        if not args.no_save:
            print()
            print("=" * 60)
            print("💾 Salvando no MongoDB...")
            print("=" * 60)
            
            try:
                mongo = MongoService()
                
                # Salvar registros
                mongo.save_batch(result['records'])
                
                # Salvar relatório
                mongo.save_report(report)
                
                mongo.close()
                
                print("✅ Dados salvos com sucesso!")
                print(f"🔗 Acesse o relatório via API: /api/v1/reports/{process_uuid}")
                
            except Exception as e:
                print(f"⚠️  Aviso: Não foi possível salvar no MongoDB")
                print(f"    Erro: {e}")
                print(f"    (Verifique as configurações no arquivo .env)")
        
        print()
        print("=" * 60)
        print("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERRO NO PROCESSAMENTO")
        print("=" * 60)
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()