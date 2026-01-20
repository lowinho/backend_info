# Multi-stage build para otimização
FROM python:3.11-slim as builder

WORKDIR /build

# Instalar dependências de compilação
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baixar modelo SpaCy (versão específica para evitar problemas)
RUN pip install --no-cache-dir \
    https://github.com/explosion/spacy-models/releases/download/pt_core_news_lg-3.7.0/pt_core_news_lg-3.7.0-py3-none-any.whl

# ============================================
# Stage final (imagem menor)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Copiar Python packages do builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código da aplicação
COPY . .

# Criar diretório de uploads
RUN mkdir -p /app/uploads

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Expor porta
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Usuário não-root (segurança)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Comando de inicialização
CMD ["python", "app.py"]