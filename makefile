.PHONY: up up-detach down down-volumes logs ps ps-all clean-dev

up: ## Start containers in the foreground
	docker-compose up

up-detach: ## Start containers in detached mode
	docker-compose up -d

down: ## Stop and remove containers
	docker-compose down

down-volumes: ## Stop and remove containers and volumes
	docker-compose down -v

logs: ## Show logs for all services
	docker-compose logs -f

ps: ## List running containers
	docker ps

ps-all: ## List all containers (running and stopped)
	docker ps -a

clean-dev: ## Clean up development environment
	 docker system prune --volumes

# Testing
test: ## Run all tests
	python -m pytest -v

test-unit: ## Run unit tests only
	python -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	python -m pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	python -m pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	python -m pytest --cov=src --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	python -m pytest-watch