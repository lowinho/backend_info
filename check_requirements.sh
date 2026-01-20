#!/bin/bash

echo "=========================================="
echo "🔍 Verificador de Pré-requisitos"
echo "=========================================="
echo ""

ERRORS=0

# Verificar Python
echo "📌 Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+')
    echo "   ✅ Python encontrado: $(python3 --version)"
    
    # Verificar versão mínima (3.8)
    if (( $(echo "$PYTHON_VERSION >= 3.8" | bc -l) )); then
        echo "   ✅ Versão adequada (>= 3.8)"
    else
        echo "   ❌ Versão muito antiga (precisa >= 3.8)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "   ❌ Python 3 não encontrado"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Verificar Docker
echo "📌 Verificando Docker..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker encontrado: $(docker --version)"
    
    # Verificar se Docker está rodando
    if docker info &> /dev/null; then
        echo "   ✅ Docker está rodando"
    else
        echo "   ⚠️  Docker instalado mas não está rodando"
        echo "      Execute: sudo systemctl start docker"
    fi
else
    echo "   ❌ Docker não encontrado"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Verificar Docker Compose
echo "📌 Verificando Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "   ✅ Docker Compose encontrado: $(docker-compose --version)"
else
    echo "   ❌ Docker Compose não encontrado"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Verificar portas
echo "📌 Verificando portas..."

# Porta 5000
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "   ⚠️  Porta 5000 em uso"
    echo "      Processo: $(lsof -Pi :5000 -sTCP:LISTEN | tail -1)"
else
    echo "   ✅ Porta 5000 disponível"
fi

# Porta 27017
if lsof -Pi :27017 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "   ⚠️  Porta 27017 em uso (MongoDB pode já estar rodando)"
else
    echo "   ✅ Porta 27017 disponível"
fi

echo ""

# Verificar arquivo .env
echo "📌 Verificando configurações..."
if [ -f ".env" ]; then
    echo "   ✅ Arquivo .env existe"
    
    # Verificar variáveis críticas
    if grep -q "MONGO_URI" .env; then
        echo "   ✅ MONGO_URI configurada"
    else
        echo "   ⚠️  MONGO_URI não encontrada no .env"
    fi
else
    echo "   ⚠️  Arquivo .env não existe"
    echo "      Execute: cp .env.example .env"
fi

echo ""

# Verificar conectividade
echo "📌 Verificando conectividade..."
if ping -c 1 github.com &> /dev/null; then
    echo "   ✅ Conectividade com GitHub OK"
else
    echo "   ⚠️  Problemas de conectividade com GitHub"
    echo "      Pode haver problemas ao baixar o modelo SpaCy"
fi

echo ""
echo "=========================================="

if [ $ERRORS -eq 0 ]; then
    echo "✅ Sistema pronto para executar!"
    echo ""
    echo "Próximos passos:"
    echo "1. Configure o arquivo .env (se ainda não fez)"
    echo "2. Execute: docker-compose up -d"
    echo "3. Acesse: http://localhost:5000/health"
else
    echo "⚠️  Foram encontrados $ERRORS problema(s)"
    echo "Corrija os erros acima antes de continuar"
fi

echo "=========================================="