import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

class MongoService:
    def __init__(self):
        # CORREÇÃO: Usando os nomes exatos que estão no seu .env
        self.uri = os.getenv("MONGO_URI")
        self.db_name = os.getenv("DB_NAME")  # Antes era MONGO_DB_NAME
        self.collection_name = os.getenv("COLLECTION_NAME") # Antes era MONGO_COLLECTION
        
        # Validação simples para garantir que carregou
        if not self.uri:
            raise ValueError("Erro: A variável MONGO_URI não foi encontrada no .env")
        if not self.db_name:
            raise ValueError("Erro: A variável DB_NAME não foi encontrada no .env")

        print(f"--- Connecting to MongoDB: {self.db_name} ---")
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Teste de conexão (Ping)
            self.client.admin.command('ping')
            print(f"MongoDB Connection: SUCCESS")
            
        except Exception as e:
            print(f"MongoDB Connection: FAILED - {e}")
            raise e

    def save_batch(self, data_list):
        if not data_list:
            print("No data to save.")
            return

        try:
            result = self.collection.insert_many(data_list)
            print(f"Successfully inserted {len(result.inserted_ids)} documents into '{self.collection_name}'.")
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")

    def close(self):
        self.client.close()