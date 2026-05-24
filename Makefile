# =============================================================================
# BoostRAG — Makefile (Linux/macOS/WSL). Người dùng Windows PowerShell có thể
# dùng `./tasks.ps1 <task>` thay vì `make <target>`.
# =============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ── Helpers ──────────────────────────────────────────────────────────────────

.PHONY: help
help:  ## Hiển thị danh sách target
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Compose ──────────────────────────────────────────────────────────────────

.PHONY: up
up:  ## Khởi động toàn bộ stack (detached)
	docker compose up -d

.PHONY: up-infra
up-infra:  ## Chỉ khởi động infra (postgres, qdrant, redis, minio)
	docker compose up -d postgres qdrant redis minio minio-init

.PHONY: down
down:  ## Stop & remove containers
	docker compose down

.PHONY: logs
logs:  ## Tail logs tất cả service
	docker compose logs -f --tail=100

.PHONY: ps
ps:  ## Liệt kê service đang chạy
	docker compose ps

# ── Backend ──────────────────────────────────────────────────────────────────

.PHONY: backend-shell
backend-shell:  ## Mở shell trong container backend
	docker compose exec backend bash

.PHONY: migrate
migrate:  ## Chạy Alembic migrate tới head
	docker compose exec backend alembic upgrade head

.PHONY: migration-new
migration-new:  ## Tạo migration mới — usage: make migration-new name="add foo"
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

.PHONY: seed
seed:  ## Seed admin user từ env SEED_ADMIN_*
	docker compose exec backend python -m app.scripts.seed_admin

.PHONY: lint-backend
lint-backend:  ## Ruff lint backend
	docker compose exec backend ruff check app/ tests/

.PHONY: format-backend
format-backend:  ## Ruff format backend
	docker compose exec backend ruff format app/ tests/

.PHONY: type-backend
type-backend:  ## Mypy type-check backend
	docker compose exec backend mypy app/

.PHONY: test-backend
test-backend:  ## Pytest backend
	docker compose exec backend pytest -q

# ── Frontend ─────────────────────────────────────────────────────────────────

.PHONY: frontend-shell
frontend-shell:  ## Mở shell trong container frontend
	docker compose exec frontend sh

.PHONY: lint-frontend
lint-frontend:  ## ESLint frontend
	docker compose exec frontend pnpm lint

.PHONY: format-frontend
format-frontend:  ## Prettier format frontend
	docker compose exec frontend pnpm format

.PHONY: type-frontend
type-frontend:  ## TS type-check frontend
	docker compose exec frontend pnpm type-check

.PHONY: test-frontend
test-frontend:  ## Vitest frontend
	docker compose exec frontend pnpm test

# ── All-in-one ───────────────────────────────────────────────────────────────

.PHONY: check
check: lint-backend type-backend test-backend lint-frontend type-frontend test-frontend  ## Lint + type + test cả 2 stack
	@echo "✓ Tất cả check pass"

.PHONY: clean
clean:  ## Xóa volumes + caches (CẨN THẬN: mất data dev)
	docker compose down -v
