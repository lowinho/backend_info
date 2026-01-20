"""
API Flask - LGPD Compliance
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
from utils.validators import validate_file_extension
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

detector = PIIDetector()
file_processor = FileProcessor(detector)
report_service = ReportService()
mongo_service = MongoService()

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================
# ROTA 1: UPLOAD
# ============================================
@app.route('/api/v1/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome de arquivo vazio'}), 400

        filename = secure_filename(file.filename)
        file_ext = validate_file_extension(filename, app.config['ALLOWED_EXTENSIONS'])
        process_uuid = str(uuid.uuid4())
        
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{process_uuid}_{filename}")
        file.save(temp_path)

        print(f"[INFO] Processando: {filename} | UUID: {process_uuid}")

        if file_ext == 'csv':
            result = file_processor.process_csv(temp_path, process_uuid)
        elif file_ext == 'txt':
            result = file_processor.process_txt(temp_path, process_uuid)
        elif file_ext in ['xlsx', 'xls']:
            result = file_processor.process_excel(temp_path, process_uuid)
        else:
            return jsonify({'error': 'Formato não suportado'}), 400

        report_data = report_service.create_report(
            process_uuid=process_uuid,
            filename=filename,
            file_type=file_ext,
            total_records=result['total_records'],
            pii_statistics=result['pii_stats'],
            processing_time=result['processing_time']
        )
        
        if 'created_at' not in report_data:
            report_data['created_at'] = datetime.now().isoformat()

        mongo_service.save_process_data(report_data, result['records'])
        os.remove(temp_path)

        return jsonify({
            'success': True,
            'message': 'Arquivo processado e salvo.',
            'process_uuid': process_uuid
        }), 201

    except Exception as e:
        app.logger.error(f"Erro no upload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ROTA 2: LISTAR RELATÓRIOS (Reports)
# ============================================
@app.route('/api/v1/reports', methods=['GET'])
def list_reports():
    try:
        limit = int(request.args.get('limit', 20))
        skip = int(request.args.get('skip', 0))
        
        reports = mongo_service.get_all_reports(limit, skip)
        total = mongo_service.count_reports()

        return jsonify({
            'success': True,
            'data': reports,
            'pagination': {'total': total, 'limit': limit, 'skip': skip}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/reports/<process_uuid>', methods=['GET'])
def get_report_detail(process_uuid):
    try:
        report = mongo_service.get_report_by_uuid(process_uuid)
        if not report:
            return jsonify({'error': 'Relatório não encontrado'}), 404
            
        return jsonify({'success': True, 'data': report})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# ROTA 3: LISTAR REGISTROS (Records)
# ============================================

# --- NOVO: LIST ALL RECORDS (GLOBAL) ---
@app.route('/api/v1/records', methods=['GET'])
def list_all_records():
    """
    Lista todos os registros processados de todos os arquivos.
    """
    try:
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))

        records = mongo_service.get_all_records(limit, skip)
        total = mongo_service.count_all_records()

        return jsonify({
            'success': True,
            'data': records,
            'pagination': {'total': total, 'limit': limit, 'skip': skip}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# REGISTROS POR UUID (JÁ EXISTENTE)
@app.route('/api/v1/reports/<process_uuid>/records', methods=['GET'])
def get_process_records(process_uuid):
    try:
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))

        records = mongo_service.get_records_by_uuid(process_uuid, limit, skip)
        total = mongo_service.count_records_by_uuid(process_uuid)

        return jsonify({
            'success': True,
            'data': records,
            'pagination': {'total': total, 'limit': limit, 'skip': skip}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"🚀 API LGPD Iniciada na porta {app.config['PORT']}")
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )