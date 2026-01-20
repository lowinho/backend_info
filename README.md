# 🔒 API de Proteção de Dados Pessoais (LGPD)

> **⚠️ AVISO IMPORTANTE:** Se encontrar erro `HTTP 404` ao fazer build do Docker relacionado ao modelo SpaCy, o Dockerfile **já foi corrigido**. Execute: `docker-compose build --no-cache && docker-compose up -d`. Para mais soluções, veja: `TROUBLESHOOTING.md` ou execute `./fix_spacy.sh`

Sistema completo de detecção e anonimização de PII (Personal Identifiable Information) em conformidade com a LGPD.

## 🎯 Funcionalidades

- ✅ Upload de arquivos CSV e TXT
- ✅ Detecção automática de 11 tipos de PII
- ✅ Anonimização inteligente preservando estrutura
- ✅ Relatórios detalhados com UUID único
- ✅ Rastreabilidade completa de dados
- ✅ Análise de risco LGPD
- ✅ API RESTful documentada

## 📋 Tipos de PII Detectados

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| CPF | Cadastro de Pessoa Física | 123.456.789-00 |
| CNPJ | Cadastro Nacional de Pessoa Jurídica | 12.345.678/0001-00 |
| RG | Registro Geral | 12.345.678-9 |
| EMAIL | Endereço de e-mail | usuario@email.com |
| PHONE | Número de telefone | (11) 98765-4321 |
| CEP | Código de Endereçamento Postal | 12345-678 |
| CREDIT_CARD | Número de cartão de crédito | 1234 5678 9012 3456 |
| SEI_PROCESS | Número de processo SEI | 12345-123456/2024-01 |
| PERSON_NAME | Nome de pessoa | João da Silva |
| LOCATION | Endereço/Localização | Rua das Flores, 123 |
| DATE_BIRTH | Data de nascimento | 01/01/1990 |

# 🚀 Instalação

## ⚠️ IMPORTANTE: Problema Conhecido com SpaCy

Se você encontrar o erro `HTTP error 404` ao fazer o build do Docker, isso é causado por rate limiting do GitHub. **O Dockerfile já foi corrigido** para usar um método mais confiável.

**Solução rápida:**
```bash
# Rebuild com cache limpo
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Se ainda houver problemas:** Consulte o arquivo `TROUBLESHOOTING.md` para soluções detalhadas.

---

## Opções de Instalação

### 1. Verificar Sistema (Recomendado)
Antes de começar, verifique se seu sistema está pronto:
```bash
./check_requirements.sh
```

### 2. Docker (Recomendado para Produção)
```bash
# Clonar repositório
git clone <repo-url>
cd pii_api

# Verificar pré-requisitos
make check

# Build e iniciar
make build
make up

# Ou usar comandos diretos:
docker-compose build --no-cache
docker-compose up -d

# API estará disponível em http://localhost:5000
```

### 3. Instalação Manual (Desenvolvimento)
```bash
# Executar script de instalação
./install.sh

# Ou manualmente:
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
python -m spacy download pt_core_news_lg

# Configurar .env
cp .env.example .env
nano .env  # Editar com suas configurações

# Iniciar MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Iniciar API
python app.py
```

### 4. Usando Makefile (Linux/Mac)
```bash
# Ver todos os comandos disponíveis
make help

# Instalar localmente
make install

# Docker (build + up)
make rebuild

# Ver logs
make logs

# Testar
make test
```

## 🐳 Comandos Docker Úteis

```bash
# Iniciar
make up
# ou
docker-compose up -d

# Ver logs
make logs
# ou
docker-compose logs -f

# Parar
make down
# ou
docker-compose down

# Restart
make restart
# ou
docker-compose restart

# Limpar tudo
make clean
# ou
docker-compose down -v
```

A API estará disponível em: `http://localhost:5000`

## 📡 Endpoints da API

### 1. Health Check
```http
GET /health
```

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-19T10:30:00",
  "services": {
    "api": "operational",
    "mongodb": "connected",
    "pii_detector": "loaded"
  }
}
```

### 2. Upload de Arquivo
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file: <arquivo.csv ou arquivo.txt>
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Arquivo processado com sucesso",
  "data": {
    "process_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "dados.csv",
    "total_records": 1000,
    "records_anonymized": 850,
    "pii_detected": {
      "CPF": 450,
      "EMAIL": 300,
      "PHONE": 250,
      "PERSON_NAME": 800
    },
    "processing_time_seconds": 12.5
  }
}
```

### 3. Listar Relatórios
```http
GET /api/v1/reports?limit=50&skip=0
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "reports": [...],
    "total": 150,
    "limit": 50,
    "skip": 0
  }
}
```

### 4. Obter Relatório Específico
```http
GET /api/v1/reports/{process_uuid}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "process_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-19T10:30:00",
    "file_info": {
      "filename": "dados.csv",
      "file_type": "csv",
      "total_records": 1000
    },
    "processing_stats": {
      "processing_time_seconds": 12.5,
      "records_per_second": 80,
      "total_pii_detected": 1800,
      "records_with_pii": 850,
      "pii_rate_percentage": 85.0
    },
    "pii_breakdown": [
      {
        "type": "PERSON_NAME",
        "description": "Nome de Pessoa",
        "count": 800,
        "percentage": 44.44
      },
      {
        "type": "CPF",
        "description": "Cadastro de Pessoa Física",
        "count": 450,
        "percentage": 25.0
      }
    ],
    "risk_assessment": {
      "level": "ALTO",
      "description": "Dados sensíveis detectados...",
      "recommendations": [
        "Implementar criptografia adicional...",
        "Restringir acesso..."
      ]
    },
    "lgpd_compliance": {
      "anonymization_applied": true,
      "data_minimization": true,
      "processing_date": "2024-01-19T10:30:00",
      "retention_policy": "Dados originais não armazenados"
    }
  }
}
```

### 5. Obter Registros por UUID
```http
GET /api/v1/records/{process_uuid}?limit=100&skip=0
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "records": [
      {
        "process_uuid": "550e8400-...",
        "record_id": "0",
        "mask_text": "João Silva, CPF 123.456.789-00",
        "text_formatted": "xxxx xxxxx, xxx xxx.xxx.xxx-xx",
        "pii_detected": {
          "PERSON_NAME": 1,
          "CPF": 1
        },
        "has_pii": true,
        "processed_at": "2024-01-19T10:30:00"
      }
    ],
    "total": 1000,
    "limit": 100,
    "skip": 0
  }
}
```

### 6. Listar Requisições Anonimizadas (Frontend)
```http
GET /api/v1/requests?limit=50&skip=0&sort=id&order=asc
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "requests": [
      {
        "id": 1,
        "text_formatted": "xxxx xxxxx mora na xxx xxx...",
        "proccess_date": "2024-01-19T10:30:00"
      }
    ],
    "total": 1500,
    "limit": 50,
    "skip": 0,
    "page": 1,
    "total_pages": 30
  }
}
```

### 7. Buscar Requisição por ID
```http
GET /api/v1/requests/123
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "text_formatted": "xxxx xxxxx mora na xxx xxx...",
    "proccess_date": "2024-01-19T10:30:00"
  }
}
```

### 8. Buscar por Texto
```http
GET /api/v1/requests/search?q=empresa&limit=50
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": 456,
        "text_formatted": "Texto que contém a palavra buscada...",
        "proccess_date": "2024-01-19T10:30:00"
      }
    ],
    "total": 15,
    "query": "empresa"
  }
}
```

**📚 Documentação detalhada:** Veja `REQUESTS_API_DOCS.md` para exemplos completos e integração frontend.
```http
GET /api/v1/records/{process_uuid}?limit=100&skip=0
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "records": [
      {
        "process_uuid": "550e8400-...",
        "record_id": "0",
        "mask_text": "João Silva, CPF 123.456.789-00",
        "text_formatted": "xxxx xxxxx, xxx xxx.xxx.xxx-xx",
        "pii_detected": {
          "PERSON_NAME": 1,
          "CPF": 1
        },
        "has_pii": true,
        "processed_at": "2024-01-19T10:30:00"
      }
    ],
    "total": 1000,
    "limit": 100,
    "skip": 0
  }
}
```

## 🗂️ Estrutura do Projeto

```
pii_api/
├── app.py                      # Aplicação Flask principal
├── config.py                   # Configurações centralizadas
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de variáveis de ambiente
├── README.md                  # Esta documentação
│
├── services/                  # Lógica de negócio
│   ├── __init__.py
│   ├── pii_detector.py       # Detector de PII com NLP
│   ├── file_processor.py     # Processador CSV/TXT
│   └── report_service.py     # Gerador de relatórios
│
├── database/                  # Camada de persistência
│   ├── __init__.py
│   └── mongo_service.py      # Operações MongoDB
│
├── utils/                     # Utilitários
│   ├── __init__.py
│   ├── validators.py         # Validadores de arquivo
│   └── exceptions.py         # Exceções customizadas
│
└── uploads/                   # Diretório temporário (criado automaticamente)
```

## 📊 Estrutura de Dados MongoDB

### Collection: `anonymized_data`
```json
{
  "process_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "record_id": "0",
  "original_id": 123,
  "mask_text": "Texto original com dados sensíveis",
  "text_formatted": "Texto anonimizado com dados xxxxxxxxxx",
  "pii_detected": {
    "CPF": 1,
    "EMAIL": 1
  },
  "has_pii": true,
  "processed_at": "2024-01-19T10:30:00"
}
```

### Collection: `processing_reports`
```json
{
  "process_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-19T10:30:00",
  "file_info": { ... },
  "processing_stats": { ... },
  "pii_breakdown": [ ... ],
  "risk_assessment": { ... },
  "lgpd_compliance": { ... }
}
```

## 🔐 Segurança e Compliance

### LGPD (Lei Geral de Proteção de Dados)

- ✅ **Minimização de Dados**: Apenas dados necessários são processados
- ✅ **Anonimização**: Dados sensíveis são substituídos por máscaras
- ✅ **Transparência**: Relatórios completos de processamento
- ✅ **Rastreabilidade**: UUID único para cada processamento
- ✅ **Não Armazenamento**: Dados originais não são mantidos

### Análise de Risco Automática

| Nível | Critério | Ações Recomendadas |
|-------|----------|-------------------|
| CRÍTICO | CPF, RG, Cartão detectados | Criptografia adicional, acesso restrito |
| ALTO | E-mail, telefone em grande volume | Documentar consentimento |
| MÉDIO | Nomes e localizações | Proteção adequada |
| BAIXO | Poucos dados sensíveis | Manter boas práticas |

## 🧪 Testes

```bash
# Executar testes
pytest

# Com cobertura
pytest --cov=. --cov-report=html
```

## 📝 Exemplo de Uso

### Python
```python
import requests

# Upload de arquivo
url = "http://localhost:5000/api/v1/upload"
files = {'file': open('dados.csv', 'rb')}
response = requests.post(url, files=files)

print(response.json())
```

### cURL
```bash
curl -X POST \
  http://localhost:5000/api/v1/upload \
  -F "file=@dados.csv"
```

### JavaScript (Frontend)
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5000/api/v1/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## 🐛 Troubleshooting

### Erro: "Language model not found"
```bash
python -m spacy download pt_core_news_lg
```

### Erro: MongoDB connection failed
- Verificar se MongoDB está rodando
- Validar MONGO_URI no .env
- Testar conexão: `mongosh <MONGO_URI>`

### Erro: "File too large"
- Ajustar MAX_FILE_SIZE no .env
- Processar arquivo em lotes menores

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudanças: `git commit -m 'Add nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

## 👥 Autores

Sistema de Proteção LGPD - v1.0.0

## 📞 Suporte

Para dúvidas ou problemas, abra uma issue no GitHub.
