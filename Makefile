run:
	docker compose -f docker-compose.dev.yml up --build -d

down:
	docker compose -f docker-compose.dev.yml down

down-v:
	docker compose -f docker-compose.dev.yml down -v

postgres:
	docker exec -it postgres_dev psql -U user -d nldb

logs:
	docker compose -f docker-compose.dev.yml logs -f

prod-local-up:
	[ -f .env.prod.local ] || cp .env.prod.local.example .env.prod.local
	docker compose --env-file .env.prod.local -f docker-compose.yml -f docker-compose.local-prod.yml up --build -d

prod-local-down:
	[ -f .env.prod.local ] || cp .env.prod.local.example .env.prod.local
	docker compose --env-file .env.prod.local -f docker-compose.yml -f docker-compose.local-prod.yml down

prod-local-down-v:
	[ -f .env.prod.local ] || cp .env.prod.local.example .env.prod.local
	docker compose --env-file .env.prod.local -f docker-compose.yml -f docker-compose.local-prod.yml down -v

prod-local-logs:
	[ -f .env.prod.local ] || cp .env.prod.local.example .env.prod.local
	docker compose --env-file .env.prod.local -f docker-compose.yml -f docker-compose.local-prod.yml logs -f

prod-local-ps:
	[ -f .env.prod.local ] || cp .env.prod.local.example .env.prod.local
	docker compose --env-file .env.prod.local -f docker-compose.yml -f docker-compose.local-prod.yml ps

precommit-install:
	pip install pre-commit ruff
	pre-commit install

precommit-run:
	pre-commit run --all-files
