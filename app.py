"""
API Flask para detecção e anonimização de PII (Personal Identifiable Information)
Autor: Sistema de Proteção LGPD
Versão: 1.0.0
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from services.pii_detector import PIIDetector
from services.file_processor import FileProcessor
from services.report_service import ReportService
from database.mongo_service import MongoService
from utils.validators import validate_file_extension, validate_file_size
from utils.exceptions import FileValidationError, ProcessingError
from config import Config

# Inicialização da aplicação
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Serviços globais
detector = PIIDetector()
file_processor = FileProcessor(detector)
report_service = ReportService()
mongo_service = MongoService()

# Garantir que os diretórios de upload existam
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/health', methods=['GET'])
def health_check():
    """Verifica o status da API e suas dependências"""
    try:
        mongo_status = mongo_service.ping()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'api': 'operational',
                'mongodb': 'connected' if mongo_status else 'disconnected',
                'pii_detector': 'loaded'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/api/v1/upload', methods=['POST'])
def upload_file():
    """
    Endpoint principal para upload e processamento de arquivos
    
    Aceita: CSV ou TXT
    Retorna: Report UUID e estatísticas de processamento
    """
    try:
        # Validação do arquivo
        if 'file' not in request.files:
            raise FileValidationError("Nenhum arquivo foi enviado")
        
        file = request.files['file']
        
        if file.filename == '':
            raise FileValidationError("Nome de arquivo vazio")
        
        # Validações
        filename = secure_filename(file.filename)
        file_ext = validate_file_extension(filename, app.config['ALLOWED_EXTENSIONS'])
        
        # Gerar UUID para o processamento
        process_uuid = str(uuid.uuid4())
        
        # Salvar arquivo temporariamente
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{process_uuid}_{filename}")
        file.save(temp_path)
        
        # Validar tamanho
        validate_file_size(temp_path, app.config['MAX_FILE_SIZE'])
        
        # Processar arquivo baseado na extensão
        print(f"[INFO] Processando arquivo: {filename} | UUID: {process_uuid}")
        
        if file_ext == 'csv':
            result = file_processor.process_csv(temp_path, process_uuid)
        elif file_ext == 'txt':
            result = file_processor.process_txt(temp_path, process_uuid)
        # NOVA LÓGICA PARA EXCEL
        elif file_ext in ['xlsx', 'xls']:
            result = file_processor.process_excel(temp_path, process_uuid)
        else:
            raise FileValidationError(f"Extensão não suportada: {file_ext}")
        
        # Salvar dados processados no MongoDB
        mongo_service.save_batch(result['records'])
        
        # Salvar também na collection access_info (formato simplificado para o frontend)
        access_info_records = []
        for record in result['records']:
            access_info_records.append({
                'id': record.get('original_id', record.get('record_id')),
                'mask_text': record.get('mask_text', ''),
                'text_formatted': record.get('text_formatted', ''),
                'proccess_date': record.get('processed_at', datetime.now().isoformat())
            })
        
        mongo_service.save_access_info_batch(access_info_records)
        
        # Gerar relatório
        report_data = report_service.create_report(
            process_uuid=process_uuid,
            filename=filename,
            file_type=file_ext,
            total_records=result['total_records'],
            pii_statistics=result['pii_stats'],
            processing_time=result['processing_time']
        )
        
        # Salvar relatório no MongoDB
        mongo_service.save_report(report_data)
        
        # Limpar arquivo temporário
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'message': 'Arquivo processado com sucesso',
            'data': {
                'process_uuid': process_uuid,
                'filename': filename,
                'total_records': result['total_records'],
                'records_anonymized': result['records_with_pii'],
                'pii_detected': result['pii_stats'],
                'processing_time_seconds': round(result['processing_time'], 2)
            }
        }), 200
        
    except FileValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation Error',
            'message': str(e)
        }), 400
        
    except ProcessingError as e:
        return jsonify({
            'success': False,
            'error': 'Processing Error',
            'message': str(e)
        }), 500
        
    except Exception as e:
        app.logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'Erro ao processar arquivo'
        }), 500


@app.route('/api/v1/reports', methods=['GET'])
def list_reports():
    """Lista todos os relatórios de processamento"""
    try:
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))
        
        reports = mongo_service.get_reports(limit=limit, skip=skip)
        total = mongo_service.count_reports()
        
        return jsonify({
            'success': True,
            'data': {
                'reports': reports,
                'total': total,
                'limit': limit,
                'skip': skip
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/reports/<process_uuid>', methods=['GET'])
def get_report(process_uuid):
    """Obtém relatório específico por UUID"""
    try:
        report = mongo_service.get_report_by_uuid(process_uuid)
        
        if not report:
            return jsonify({
                'success': False,
                'message': 'Relatório não encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'data': report
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/records/<process_uuid>', methods=['GET'])
def get_records_by_process(process_uuid):
    """Obtém todos os registros de um processamento específico"""
    try:
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        records = mongo_service.get_records_by_uuid(
            process_uuid=process_uuid,
            limit=limit,
            skip=skip
        )
        
        total = mongo_service.count_records_by_uuid(process_uuid)
        
        return jsonify({
            'success': True,
            'data': {
                'records': records,
                'total': total,
                'limit': limit,
                'skip': skip
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/requests', methods=['GET'])
def get_all_requests():
    """
    Obtém todas as requisições anonimizadas (equivalente ao getAllRequests do Node)
    
    Query params opcionais:
    - limit: Número máximo de registros (default: 100)
    - skip: Número de registros a pular para paginação (default: 0)
    - sort: Campo para ordenação (default: id)
    - order: asc ou desc (default: asc)
    """
    try:
        # Parâmetros de paginação
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'asc')
        
        # Buscar registros
        requests = mongo_service.get_all_access_requests(
            limit=limit,
            skip=skip,
            sort_field=sort_field,
            sort_order=sort_order
        )
        
        total = mongo_service.count_access_requests()
        
        return jsonify({
            'success': True,
            'data': {
                'requests': requests,
                'total': total,
                'limit': limit,
                'skip': skip,
                'page': (skip // limit) + 1 if limit > 0 else 1,
                'total_pages': (total // limit) + 1 if limit > 0 else 1
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar requisições: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/requests/<int:request_id>', methods=['GET'])
def get_request_by_id(request_id):
    """
    Obtém uma requisição específica por ID (equivalente ao getRequestById do Node)
    
    Args:
        request_id: ID numérico da requisição
    """
    try:
        request_data = mongo_service.get_access_request_by_id(request_id)
        
        if not request_data:
            return jsonify({
                'success': False,
                'message': f'Requisição com ID {request_id} não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': request_data
        }), 200
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar requisição {request_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/requests/search', methods=['GET'])
def search_requests():
    """
    Busca requisições por texto (busca no text_formatted)
    
    Query params:
    - q: Texto para buscar
    - limit: Número máximo de resultados (default: 50)
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 50))
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Parâmetro "q" (query) é obrigatório'
            }), 400
        
        results = mongo_service.search_access_requests(query, limit)
        
        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'total': len(results),
                'query': query
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar requisições: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': 'Endpoint não encontrado'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': 'Erro interno do servidor'
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🔒 API de Proteção de Dados (LGPD)")
    print("=" * 60)
    print(f"📍 Ambiente: {app.config['ENV']}")
    print(f"🗄️  Database: {app.config['DB_NAME']}")
    print(f"📂 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print("=" * 60)
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
