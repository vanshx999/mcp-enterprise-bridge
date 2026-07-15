.PHONY: up down build restart logs test test-backend frontend-build shell-db shell-backend logs-backend logs-caddy ps clean

# Default target
help:
	@echo "MCP Enterprise Bridge - Development Commands"
	@echo "============================================"
	@echo ""
	@echo "  make up              Start all services (docker compose up -d)"
	@echo "  make down            Stop all services"
	@echo "  make build           Rebuild backend image"
	@echo "  make restart         Rebuild + restart backend"
	@echo "  make logs            Tail all logs"
	@echo "  make test            Run all backend tests"
	@echo "  make test-backend    Alias for test"
	@echo "  make frontend-build  Build frontend for production"
	@echo "  make shell-db        Open psql shell"
	@echo "  make shell-backend   Open bash in backend container"
	@echo "  make logs-backend    Tail backend logs"
	@echo "  make logs-caddy      Tail Caddy logs"
	@echo "  make ps              Show container status"
	@echo "  make clean           Remove all containers, volumes, images"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build backend

restart:
	docker compose up -d --build backend

logs:
	docker compose logs -f

test: test-backend

test-backend:
	docker compose exec backend python -m pytest -v

frontend-build:
	docker compose exec frontend npm run build

shell-db:
	docker compose exec postgres psql -U postgres -d mcp_bridge

shell-backend:
	docker compose exec backend bash

logs-backend:
	docker compose logs -f backend

logs-caddy:
	docker compose logs -f caddy

ps:
	docker compose ps

clean:
	docker compose down -v --rmi all
