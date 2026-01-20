.PHONY: help install check build up down restart logs clean test

# Cores para output
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Mostrar ajuda
	@echo "=========================================="
	@echo "  API de Proteção LGPD - Comandos"
	@echo "=========================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2}'
	@echo ""

check: ## Verificar pré-requisitos
	@echo "${YELLOW}Verificando sistema...${NC}"
	@./check_requirements.sh

install: ## Instalar dependências (local)
	@echo "${YELLOW}Instalando dependências...${NC}"
	@./install.sh

build: ## Build das imagens Docker
	@echo "${YELLOW}Building Docker images...${NC}"
	@docker-compose build --no-cache

up: ## Iniciar containers
	@echo "${YELLOW}Iniciando containers...${NC}"
	@docker-compose up -d
	@echo "${GREEN}✅ Containers iniciados!${NC}"
	@echo "API: http://localhost:5000"
	@echo "Health: http://localhost:5000/health"

down: ## Parar containers
	@echo "${YELLOW}Parando containers...${NC}"
	@docker-compose down
	@echo "${GREEN}✅ Containers parados!${NC}"

restart: ## Reiniciar containers
	@echo "${YELLOW}Reiniciando containers...${NC}"
	@docker-compose restart
	@echo "${GREEN}✅ Containers reiniciados!${NC}"

logs: ## Ver logs
	@docker-compose logs -f

logs-api: ## Ver logs da API
	@docker-compose logs -f api

logs-mongo: ## Ver logs do MongoDB
	@docker-compose logs -f mongodb

clean: ## Limpar tudo (containers, volumes, imagens)
	@echo "${YELLOW}Limpando containers, volumes e imagens...${NC}"
	@docker-compose down -v
	@docker rmi pii_api_api 2>/dev/null || true
	@echo "${GREEN}✅ Limpeza concluída!${NC}"

rebuild: clean build up ## Limpar e reconstruir tudo

test: ## Testar API
	@echo "${YELLOW}Testando API...${NC}"
	@curl -s http://localhost:5000/health | jq . || echo "API não está respondendo"

test-upload: ## Testar upload (precisa de arquivo test.csv)
	@echo "${YELLOW}Testando upload...${NC}"
	@curl -X POST http://localhost:5000/api/v1/upload -F "file=@test.csv" | jq .

shell: ## Acessar shell do container API
	@docker exec -it lgpd_api bash

shell-mongo: ## Acessar shell do MongoDB
	@docker exec -it lgpd_mongodb mongosh

ps: ## Ver status dos containers
	@docker-compose ps

dev: ## Rodar em modo desenvolvimento (local)
	@echo "${YELLOW}Iniciando em modo desenvolvimento...${NC}"
	@source venv/bin/activate && python app.py

process: ## Processar arquivo local (ex: make process FILE=dados.csv)
	@python process_file.py --file $(FILE)

backup-mongo: ## Backup do MongoDB
	@echo "${YELLOW}Fazendo backup do MongoDB...${NC}"
	@docker exec lgpd_mongodb mongodump --out=/data/backup
	@docker cp lgpd_mongodb:/data/backup ./backup_$(shell date +%Y%m%d_%H%M%S)
	@echo "${GREEN}✅ Backup concluído!${NC}"

restore-mongo: ## Restaurar MongoDB (ex: make restore-mongo BACKUP=backup_20240119)
	@echo "${YELLOW}Restaurando MongoDB...${NC}"
	@docker cp $(BACKUP) lgpd_mongodb:/data/restore
	@docker exec lgpd_mongodb mongorestore /data/restore
	@echo "${GREEN}✅ Restauração concluída!${NC}"

stats: ## Ver estatísticas dos containers
	@docker stats lgpd_api lgpd_mongodb --no-stream

update: ## Atualizar dependências
	@pip install -r requirements.txt --upgrade

lint: ## Verificar código (se tiver pylint instalado)
	@pylint services/ database/ utils/ || true

format: ## Formatar código (se tiver black instalado)
	@black services/ database/ utils/ app.py config.py || true

docs: ## Abrir documentação
	@echo "Abrindo documentação..."
	@xdg-open README.md 2>/dev/null || open README.md 2>/dev/null || echo "Abra manualmente: README.md"

frontend: ## Abrir frontend de exemplo
	@echo "Abrindo frontend..."
	@xdg-open frontend_example.html 2>/dev/null || open frontend_example.html 2>/dev/null || echo "Abra manualmente: frontend_example.html"