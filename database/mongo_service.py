"""
Serviço de persistência MongoDB - Otimizado para LGPD
"""
import os
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv
from typing import List, Dict, Optional
from config import Config

load_dotenv()

class MongoService:
    def __init__(self):
        self.uri = Config.MONGO_URI
        self.db_name = Config.DB_NAME
        
        # Collection para os registros individuais (Mensagens/Textos)
        self.records_collection_name = Config.ACCESS_INFO_COLLECTION
        
        # Collection para o relatório consolidado (Stats/Compliance)
        self.reports_collection_name = Config.REPORTS_COLLECTION
        
        if not self.uri:
            raise ValueError("MONGO_URI não configurada")
        
        print(f"🔌 Conectando ao MongoDB: {self.db_name}")
        
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            
            # Definição das Collections
            self.records = self.db[self.records_collection_name]
            self.reports = self.db[self.reports_collection_name]
            
            # Teste de conexão
            self.client.admin.command('ping')
            print(f"✅ MongoDB conectado com sucesso")
            
            self._create_indexes()
            
        except ConnectionFailure as e:
            print(f"❌ Falha na conexão com MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Cria índices essenciais"""
        try:
            # Índices para os Registros
            self.records.create_index("process_uuid")
            self.records.create_index("processed_at") # Útil para ordenação global
            self.records.create_index([("process_uuid", 1), ("record_id", 1)])
            
            # Índices para os Relatórios
            self.reports.create_index("process_uuid", unique=True)
            self.reports.create_index([("created_at", DESCENDING)])
            
            print("✅ Índices verificados")
        except OperationFailure as e:
            print(f"⚠️ Aviso ao criar índices: {e}")

    def ping(self) -> bool:
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    # ==========================================
    # 1. SALVAR DADOS
    # ==========================================

    def save_process_data(self, report_data: Dict, records_data: List[Dict]) -> bool:
        try:
            self.reports.insert_one(report_data)
            if records_data:
                self.records.insert_many(records_data, ordered=False)
            print(f"✅ Processamento {report_data['process_uuid']} salvo.")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")
            return False

    # ==========================================
    # 2. RELATÓRIOS (Reports)
    # ==========================================

    def get_all_reports(self, limit: int = 50, skip: int = 0) -> List[Dict]:
        try:
            cursor = self.reports.find({}, {'_id': 0})\
                .sort('created_at', DESCENDING)\
                .skip(skip)\
                .limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"❌ Erro ao listar relatórios: {e}")
            return []

    def get_report_by_uuid(self, process_uuid: str) -> Optional[Dict]:
        try:
            return self.reports.find_one({'process_uuid': process_uuid}, {'_id': 0})
        except Exception as e:
            print(f"❌ Erro ao buscar relatório: {e}")
            return None

    def count_reports(self) -> int:
        return self.reports.count_documents({})

    # ==========================================
    # 3. REGISTROS (Records/Mensagens)
    # ==========================================

    def get_records_by_uuid(self, process_uuid: str, limit: int = 100, skip: int = 0) -> List[Dict]:
        """Retorna registros de um processamento específico"""
        try:
            cursor = self.records.find(
                {'process_uuid': process_uuid},
                {'_id': 0}
            ).skip(skip).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"❌ Erro ao buscar registros do processo: {e}")
            return []

    def count_records_by_uuid(self, process_uuid: str) -> int:
        return self.records.count_documents({'process_uuid': process_uuid})

    # --- NOVO: LIST ALL RECORDS (GLOBAL) ---
    def get_all_records(self, limit: int = 100, skip: int = 0) -> List[Dict]:
        """Retorna todos os registros do sistema (paginado)"""
        try:
            # Ordena pelos mais recentes (assumindo que existe processed_at ou similar, senão usa padrão)
            cursor = self.records.find({}, {'_id': 0})\
                .sort('processed_at', DESCENDING)\
                .skip(skip)\
                .limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"❌ Erro ao buscar todos os registros: {e}")
            return []

    def count_all_records(self) -> int:
        """Conta total de registros no banco inteiro"""
        return self.records.count_documents({})