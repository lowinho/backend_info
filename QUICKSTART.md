# 🚀 Guia Rápido de Uso

## Instalação Rápida

### Opção 1: Docker (Recomendado)
```bash
# Clonar repositório
git clone <repo-url>
cd pii_api

# Iniciar com Docker Compose
docker-compose up -d

# API estará disponível em http://localhost:5000
```

### Opção 2: Instalação Manual
```bash
# Executar script de instalação
./install.sh

# Ativar ambiente virtual
source venv/bin/activate

# Configurar .env
cp .env.example .env
nano .env  # Editar com suas configurações

# Iniciar MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Iniciar API
python app.py
```

## Uso da API

### 1. Testar Conexão
```bash
curl http://localhost:5000/health
```

### 2. Fazer Upload de CSV
```bash
curl -X POST http://localhost:5000/api/v1/upload \
  -F "file=@meu_arquivo.csv"
```

### 3. Fazer Upload de TXT
```bash
curl -X POST http://localhost:5000/api/v1/upload \
  -F "file=@meu_arquivo.txt"
```

### 4. Listar Relatórios
```bash
curl http://localhost:5000/api/v1/reports
```

### 5. Obter Relatório Específico
```bash
curl http://localhost:5000/api/v1/reports/UUID_AQUI
```

### 6. Obter Registros Processados
```bash
curl http://localhost:5000/api/v1/records/UUID_AQUI
```

## Uso do Script Standalone

### Processar arquivo local (sem API)
```bash
# Processar CSV
python process_file.py --file dados.csv

# Processar TXT
python process_file.py --file dados.txt

# Processar sem salvar no MongoDB
python process_file.py --file dados.csv --no-save
```

## Frontend de Teste

Abra o arquivo `frontend_example.html` no navegador para uma interface visual de teste.

## Estrutura de Dados

### Entrada CSV (exemplo)
```csv
ID,Texto Mascarado
1,"João Silva mora na Rua ABC, 123. CPF: 123.456.789-00"
2,"Maria Santos, email: maria@email.com, tel: (11) 98765-4321"
```

### Saída (MongoDB)
```json
{
  "process_uuid": "550e8400-...",
  "record_id": "0",
  "mask_text": "João Silva mora na Rua ABC, 123. CPF: 123.456.789-00",
  "text_formatted": "xxxx xxxxx mora na xxx xxx, xxx. xxx: xxx.xxx.xxx-xx",
  "pii_detected": {
    "PERSON_NAME": 1,
    "LOCATION": 1,
    "CPF": 1
  },
  "has_pii": true
}
```

## Tipos de PII Detectados

| Código | Descrição | Exemplo |
|--------|-----------|---------|
| CPF | Cadastro de Pessoa Física | 123.456.789-00 |
| CNPJ | Cadastro Nacional de Pessoa Jurídica | 12.345.678/0001-00 |
| RG | Registro Geral | 12.345.678-9 |
| EMAIL | Endereço de e-mail | usuario@email.com |
| PHONE | Telefone | (11) 98765-4321 |
| CEP | CEP | 12345-678 |
| CREDIT_CARD | Cartão de crédito | 1234 5678 9012 3456 |
| SEI_PROCESS | Processo SEI | 12345-123456/2024-01 |
| PERSON_NAME | Nome de pessoa | João da Silva |
| LOCATION | Localização | Rua ABC, 123 |
| DATE_BIRTH | Data de nascimento | 01/01/1990 |

## Níveis de Risco

- **CRÍTICO**: CPF, RG, Cartão detectados
- **ALTO**: E-mail, telefone em grande volume
- **MÉDIO**: Nomes e localizações
- **BAIXO**: Poucos dados sensíveis
- **MÍNIMO**: Nenhum dado sensível significativo

## Troubleshooting

### Erro: "Language model not found"
```bash
python -m spacy download pt_core_news_lg
```

### Erro: MongoDB não conecta
```bash
# Verificar se MongoDB está rodando
docker ps | grep mongo

# Iniciar MongoDB
docker start mongodb
```

### Erro: "Port 5000 already in use"
Edite o arquivo `.env` e altere `FLASK_PORT=5000` para outra porta.

## Exemplos de Integração

### Python
```python
import requests

files = {'file': open('dados.csv', 'rb')}
response = requests.post('http://localhost:5000/api/v1/upload', files=files)
print(response.json())
```

### JavaScript
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5000/api/v1/upload', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(data => console.log(data));
```

### cURL com relatório
```bash
# Upload e capturar UUID
UUID=$(curl -s -X POST http://localhost:5000/api/v1/upload \
  -F "file=@dados.csv" | jq -r '.data.process_uuid')

# Obter relatório
curl http://localhost:5000/api/v1/reports/$UUID | jq .
```

## Configurações Importantes

### Variáveis de Ambiente (.env)
```env
# MongoDB
MONGO_URI=mongodb://localhost:27017/
DB_NAME=lgpd_database

# Upload
MAX_FILE_SIZE=52428800  # 50MB
DEFAULT_CSV_COLUMN=Texto Mascarado

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True
```

## Próximos Passos

1. ✅ Configurar backup automático do MongoDB
2. ✅ Implementar autenticação JWT
3. ✅ Adicionar webhook para notificações
4. ✅ Criar dashboard de visualização
5. ✅ Implementar exportação de relatórios em PDF

## Suporte

- 📧 Email: suporte@exemplo.com
- 📚 Documentação: README.md
- 🐛 Issues: GitHub Issues
- 💬 Discussões: GitHub Discussions