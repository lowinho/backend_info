"""
Serviço de persistência MongoDB
"""
import os
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv
from typing import List, Dict, Optional
from config import Config

load_dotenv()


class MongoService:
    """Gerencia todas as operações com MongoDB"""
    
    def __init__(self):
        """Inicializa conexão com MongoDB"""
        self.uri = Config.MONGO_URI
        self.db_name = Config.DB_NAME
        self.collection_name = Config.COLLECTION_NAME
        self.reports_collection_name = Config.REPORTS_COLLECTION
        self.access_info_collection_name = Config.ACCESS_INFO_COLLECTION
        
        if not self.uri:
            raise ValueError("MONGO_URI não configurada")
        
        print(f"🔌 Conectando ao MongoDB: {self.db_name}")
        
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.reports = self.db[self.reports_collection_name]
            self.access_info = self.db[self.access_info_collection_name]  # Nova collection
            
            # Teste de conexão
            self.client.admin.command('ping')
            print(f"✅ MongoDB conectado com sucesso")
            
            # Criar índices para performance
            self._create_indexes()
            
        except ConnectionFailure as e:
            print(f"❌ Falha na conexão com MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Cria índices para otimizar consultas"""
        try:
            # Índices na collection de dados
            self.collection.create_index("process_uuid")
            self.collection.create_index("processed_at")
            self.collection.create_index([("process_uuid", 1), ("record_id", 1)], unique=True)
            
            # Índices na collection de relatórios
            self.reports.create_index("process_uuid", unique=True)
            self.reports.create_index("created_at")
            self.reports.create_index([("created_at", DESCENDING)])
            
            # Índices na collection access_info
            self.access_info.create_index("id", unique=True)
            self.access_info.create_index("proccess_date")
            self.access_info.create_index([("id", 1)])  # Para ordenação
            # Índice de texto para busca
            self.access_info.create_index([("text_formatted", "text")])
            
            print("✅ Índices MongoDB criados")
        except OperationFailure as e:
            print(f"⚠️  Aviso ao criar índices: {e}")
    
    def ping(self) -> bool:
        """Verifica se a conexão está ativa"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def save_batch(self, records: List[Dict]) -> bool:
        """
        Salva lote de registros anonimizados
        
        Args:
            records: Lista de dicionários com dados
            
        Returns:
            True se sucesso
        """
        if not records:
            print("⚠️  Nenhum registro para salvar")
            return False
        
        try:
            result = self.collection.insert_many(records, ordered=False)
            print(f"✅ {len(result.inserted_ids)} registros salvos em '{self.collection_name}'")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar registros: {e}")
            return False
    
    def save_report(self, report: Dict) -> bool:
        """
        Salva relatório de processamento
        
        Args:
            report: Dicionário com dados do relatório
            
        Returns:
            True se sucesso
        """
        try:
            result = self.reports.insert_one(report)
            print(f"✅ Relatório salvo: {report['process_uuid']}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
            return False
    
    def get_reports(self, limit: int = 50, skip: int = 0) -> List[Dict]:
        """
        Lista relatórios de processamento
        
        Args:
            limit: Número máximo de registros
            skip: Número de registros a pular
            
        Returns:
            Lista de relatórios
        """
        try:
            cursor = self.reports.find(
                {},
                {'_id': 0}  # Excluir _id do MongoDB
            ).sort('created_at', DESCENDING).skip(skip).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"❌ Erro ao buscar relatórios: {e}")
            return []
    
    def get_report_by_uuid(self, process_uuid: str) -> Optional[Dict]:
        """
        Busca relatório específico por UUID
        
        Args:
            process_uuid: UUID do processamento
            
        Returns:
            Dicionário com relatório ou None
        """
        try:
            report = self.reports.find_one(
                {'process_uuid': process_uuid},
                {'_id': 0}
            )
            return report
        except Exception as e:
            print(f"❌ Erro ao buscar relatório: {e}")
            return None
    
    def get_records_by_uuid(
        self, 
        process_uuid: str, 
        limit: int = 100, 
        skip: int = 0
    ) -> List[Dict]:
        """
        Busca registros de um processamento específico
        
        Args:
            process_uuid: UUID do processamento
            limit: Número máximo de registros
            skip: Número de registros a pular
            
        Returns:
            Lista de registros
        """
        try:
            cursor = self.collection.find(
                {'process_uuid': process_uuid},
                {'_id': 0}
            ).skip(skip).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"❌ Erro ao buscar registros: {e}")
            return []
    
    def count_reports(self) -> int:
        """Conta total de relatórios"""
        try:
            return self.reports.count_documents({})
        except Exception as e:
            print(f"❌ Erro ao contar relatórios: {e}")
            return 0
    
    def count_records_by_uuid(self, process_uuid: str) -> int:
        """Conta registros de um processamento específico"""
        try:
            return self.collection.count_documents({'process_uuid': process_uuid})
        except Exception as e:
            print(f"❌ Erro ao contar registros: {e}")
            return 0
    
    def delete_by_uuid(self, process_uuid: str) -> bool:
        """
        Remove todos os dados de um processamento
        
        Args:
            process_uuid: UUID do processamento
            
        Returns:
            True se sucesso
        """
        try:
            # Remover registros
            records_result = self.collection.delete_many({'process_uuid': process_uuid})
            
            # Remover relatório
            report_result = self.reports.delete_one({'process_uuid': process_uuid})
            
            print(f"✅ Removidos {records_result.deleted_count} registros e {report_result.deleted_count} relatório")
            return True
        except Exception as e:
            print(f"❌ Erro ao remover dados: {e}")
            return False
    
    # ============================================
    # MÉTODOS PARA ACCESS_INFO COLLECTION
    # ============================================
    
    def save_access_info_batch(self, records: List[Dict]) -> bool:
        """
        Salva lote de registros na collection access_info
        
        Args:
            records: Lista de dicionários com dados (id, mask_text, text_formatted, proccess_date)
            
        Returns:
            True se sucesso
        """
        if not records:
            print("⚠️  Nenhum registro para salvar em access_info")
            return False
        
        try:
            # Usar upsert para evitar duplicatas
            operations = []
            for record in records:
                operations.append(
                    {
                        'updateOne': {
                            'filter': {'id': record['id']},
                            'update': {'$set': record},
                            'upsert': True
                        }
                    }
                )
            
            result = self.access_info.bulk_write(operations)
            inserted = result.upserted_count + result.modified_count
            print(f"✅ {inserted} registros salvos/atualizados em '{self.access_info_collection_name}'")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar access_info: {e}")
            return False
    
    def get_all_access_requests(
        self, 
        limit: int = 100, 
        skip: int = 0,
        sort_field: str = 'id',
        sort_order: str = 'asc'
    ) -> List[Dict]:
        """
        Lista todas as requisições da collection access_info
        Equivalente ao getAllRequests() do Node.js
        
        Args:
            limit: Número máximo de registros
            skip: Número de registros a pular
            sort_field: Campo para ordenação
            sort_order: 'asc' ou 'desc'
            
        Returns:
            Lista de requisições (apenas id, text_formatted, proccess_date)
        """
        try:
            sort_direction = 1 if sort_order == 'asc' else -1
            
            cursor = self.access_info.find(
                {},
                {
                    '_id': 0,  # Excluir _id do MongoDB
                    'id': 1,
                    'text_formatted': 1,
                    'proccess_date': 1
                }
            ).sort(sort_field, sort_direction).skip(skip).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"❌ Erro ao buscar access requests: {e}")
            return []
    
    def get_access_request_by_id(self, request_id: int) -> Optional[Dict]:
        """
        Busca requisição específica por ID
        Equivalente ao getRequestById() do Node.js
        
        Args:
            request_id: ID numérico da requisição
            
        Returns:
            Dicionário com dados da requisição ou None
        """
        try:
            request = self.access_info.find_one(
                {'id': request_id},
                {
                    '_id': 0,
                    'id': 1,
                    'text_formatted': 1,
                    'proccess_date': 1
                }
            )
            return request
        except Exception as e:
            print(f"❌ Erro ao buscar access request {request_id}: {e}")
            return None
    
    def count_access_requests(self) -> int:
        """Conta total de requisições na access_info"""
        try:
            return self.access_info.count_documents({})
        except Exception as e:
            print(f"❌ Erro ao contar access requests: {e}")
            return 0
    
    def search_access_requests(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Busca requisições por texto no campo text_formatted
        
        Args:
            query: Texto para buscar
            limit: Número máximo de resultados
            
        Returns:
            Lista de requisições que correspondem à busca
        """
        try:
            cursor = self.access_info.find(
                {'$text': {'$search': query}},
                {
                    '_id': 0,
                    'id': 1,
                    'text_formatted': 1,
                    'proccess_date': 1,
                    'score': {'$meta': 'textScore'}
                }
            ).sort([('score', {'$meta': 'textScore'})]).limit(limit)
            
            return list(cursor)
        except Exception as e:
            # Se índice de texto não existir, fazer busca com regex
            print(f"⚠️  Busca por texto falhou, usando regex: {e}")
            try:
                cursor = self.access_info.find(
                    {'text_formatted': {'$regex': query, '$options': 'i'}},
                    {
                        '_id': 0,
                        'id': 1,
                        'text_formatted': 1,
                        'proccess_date': 1
                    }
                ).limit(limit)
                return list(cursor)
            except Exception as e2:
                print(f"❌ Erro ao buscar com regex: {e2}")
                return []
    
    def close(self):
        """Fecha conexão com MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 Conexão MongoDB fechada")
