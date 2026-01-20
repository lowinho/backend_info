#!/bin/bash

echo "=========================================="
echo "🔒 Instalador API LGPD"
echo "=========================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Criar ambiente virtual
echo "📦 Criando ambiente virtual..."
python3 -m venv venv

# Ativar ambiente virtual
echo "🔌 Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo "⬆️  Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo "📚 Instalando dependências..."
pip install -r requirements.txt

# Baixar modelo NLP
echo "🤖 Baixando modelo NLP (português)..."
python -m spacy download pt_core_news_lg

# Criar arquivo .env
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️  IMPORTANTE: Configure suas variáveis no arquivo .env"
fi

echo ""
echo "=========================================="
echo "✅ Instalação concluída!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "1. Configure o arquivo .env com suas credenciais"
echo "2. Inicie o MongoDB (docker run -d -p 27017:27017 mongo:latest)"
echo "3. Execute: python app.py"
echo ""
echo "Para ativar o ambiente virtual:"
echo "  source venv/bin/activate  # Linux/Mac"
echo "  venv\\Scripts\\activate     # Windows"
echo ""