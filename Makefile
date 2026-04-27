.PHONY: help dev-up dev-down dev-logs test lint fmt typecheck migrate build clean

SERVICES := gateway auth projects timelog billing resources notifications
DOCKER_COMPOSE := docker compose

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  dev-up        Start all services (Docker Compose)"
	@echo "  dev-down      Stop all services"
	@echo "  dev-logs      Tail logs for all services"
	@echo "  migrate       Run alembic upgrade head for all services"
	@echo "  test          Run all test suites"
	@echo "  lint          Run ruff linter"
	@echo "  fmt           Run ruff formatter"
	@echo "  typecheck     Run mypy"
	@echo "  build         Build all Docker images"
	@echo "  clean         Remove containers, volumes, images"

dev-up:
	$(DOCKER_COMPOSE) up -d --build
	@echo "Stack is up. Gateway at http://localhost:8000"

dev-down:
	$(DOCKER_COMPOSE) down

dev-logs:
	$(DOCKER_COMPOSE) logs -f

migrate:
	@for svc in $(SERVICES); do \
		if [ "$$svc" != "gateway" ]; then \
			echo "→ Migrating $$svc..."; \
			$(DOCKER_COMPOSE) exec $$svc alembic upgrade head; \
		fi; \
	done

test:
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner

test-local:
	@for svc in $(SERVICES); do \
		if [ "$$svc" != "gateway" ]; then \
			echo "→ Testing $$svc..."; \
			cd services/$$svc && python -m pytest app/tests/ -v --tb=short; cd ../..; \
		fi; \
	done

lint:
	ruff check services/ shared/

fmt:
	ruff format services/ shared/

typecheck:
	mypy services/ shared/ --ignore-missing-imports

build:
	@for svc in $(SERVICES); do \
		echo "→ Building $$svc..."; \
		docker build services/$$svc --target production -t consulting-pm/$$svc:local; \
	done

clean:
	$(DOCKER_COMPOSE) down -v --rmi local
