# 🔧 Troubleshooting - Docker & SpaCy

## ❌ Problema: Erro ao baixar modelo SpaCy no Docker

### Sintoma
```
ERROR: HTTP error 404 while getting https://github.com/explosion/spacy-models/releases/download/...
```

### Causas Comuns
1. Rate limit do GitHub
2. Problemas de rede durante o build
3. Versão incorreta do modelo

---

## ✅ Soluções

### Solução 1: Usar Dockerfile corrigido (Recomendado)
O Dockerfile já foi atualizado para baixar o modelo via URL direto do wheel:

```bash
# Reconstruir imagem
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Solução 2: Usar Dockerfile otimizado (Multi-stage)
```bash
# Usar versão otimizada
mv Dockerfile Dockerfile.original
mv Dockerfile.optimized Dockerfile

# Build
docker-compose build --no-cache
docker-compose up -d
```

### Solução 3: Download manual do modelo
Se ainda houver problemas, baixe o modelo manualmente:

```bash
# 1. Baixar modelo
wget https://github.com/explosion/spacy-models/releases/download/pt_core_news_lg-3.7.0/pt_core_news_lg-3.7.0-py3-none-any.whl

# 2. Copiar para o diretório do projeto
mv pt_core_news_lg-3.7.0-py3-none-any.whl pii_api/

# 3. Modificar Dockerfile
# Adicionar após COPY requirements.txt:
# COPY pt_core_news_lg-3.7.0-py3-none-any.whl .
# RUN pip install pt_core_news_lg-3.7.0-py3-none-any.whl

# 4. Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Solução 4: Instalar modelo após container estar rodando
```bash
# 1. Subir container sem modelo (remover linha do Dockerfile)
docker-compose up -d

# 2. Entrar no container
docker exec -it lgpd_api bash

# 3. Instalar modelo manualmente
pip install https://github.com/explosion/spacy-models/releases/download/pt_core_news_lg-3.7.0/pt_core_news_lg-3.7.0-py3-none-any.whl

# 4. Reiniciar container
docker-compose restart api
```

### Solução 5: Usar modelo menor (temporário)
Se precisar rodar urgentemente, use o modelo menor:

```python
# No arquivo services/pii_detector.py, trocar:
# self.nlp = spacy.load("pt_core_news_lg")
# por:
self.nlp = spacy.load("pt_core_news_sm")
```

```bash
# Dockerfile: trocar pt_core_news_lg por pt_core_news_sm
# Depois:
docker-compose build
docker-compose up -d
```

---

## 🐛 Outros Problemas Comuns

### Problema: "Port 5000 already in use"
```bash
# Verificar o que está usando a porta
lsof -i :5000
# ou
netstat -tulpn | grep 5000

# Matar processo
kill -9 <PID>

# Ou mudar porta no .env
FLASK_PORT=5001
```

### Problema: MongoDB não conecta
```bash
# Verificar se está rodando
docker ps | grep mongo

# Ver logs
docker logs lgpd_mongodb

# Reiniciar
docker-compose restart mongodb

# Verificar conexão
docker exec -it lgpd_mongodb mongosh
```

### Problema: Container sai imediatamente
```bash
# Ver logs
docker-compose logs api

# Modo debug
docker-compose up api  # sem -d

# Entrar no container
docker-compose run api /bin/bash
```

### Problema: Erro de permissão no /uploads
```bash
# Dar permissão
chmod 777 uploads/

# Ou no Dockerfile adicionar:
RUN chmod -R 777 /app/uploads
```

---

## 📝 Comandos Úteis

### Limpar tudo e recomeçar
```bash
# Parar e remover containers
docker-compose down -v

# Remover imagens
docker rmi pii_api_api

# Limpar cache do Docker
docker system prune -a

# Rebuild do zero
docker-compose build --no-cache
docker-compose up -d
```

### Verificar saúde da aplicação
```bash
# Health check
curl http://localhost:5000/health

# Logs em tempo real
docker-compose logs -f api

# Status dos containers
docker-compose ps
```

### Acessar container
```bash
# Bash
docker exec -it lgpd_api bash

# Python interativo
docker exec -it lgpd_api python

# Ver processos
docker exec -it lgpd_api ps aux
```

---

## 🔄 Alternativa: Executar SEM Docker

Se os problemas persistirem, execute localmente:

```bash
cd pii_api

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Baixar modelo
python -m spacy download pt_core_news_lg

# Configurar .env
cp .env.example .env
nano .env

# Rodar MongoDB separadamente
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Iniciar API
python app.py
```

---

## 📞 Precisa de Ajuda?

Se nenhuma solução funcionar:

1. **Verifique os logs completos:**
   ```bash
   docker-compose logs api > logs.txt
   ```

2. **Teste a instalação local do SpaCy:**
   ```bash
   python -m spacy download pt_core_news_lg
   python -c "import spacy; nlp = spacy.load('pt_core_news_lg'); print('OK!')"
   ```

3. **Verifique versões:**
   ```bash
   python --version  # Deve ser 3.8+
   pip --version
   docker --version
   docker-compose --version
   ```

4. **Compartilhe o erro completo** para diagnóstico mais preciso.

---

## ✅ Checklist de Verificação

- [ ] Python 3.8+ instalado
- [ ] Docker e Docker Compose instalados
- [ ] Porta 5000 disponível
- [ ] Porta 27017 disponível (MongoDB)
- [ ] Arquivo .env configurado
- [ ] Modelo SpaCy baixado com sucesso
- [ ] MongoDB rodando
- [ ] API respondendo em /health

---

**Dica:** O Dockerfile já foi corrigido para usar o método mais confiável de instalação do modelo SpaCy!