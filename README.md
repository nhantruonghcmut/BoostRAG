# BoostRAG

> Enterprise RAG system với access control, multi-provider LLM, và admin portal.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

---

## Tổng quan

**BoostRAG** là hệ thống RAG (Retrieval-Augmented Generation) cấp doanh nghiệp. Admin upload và phân quyền tài liệu; user chat với tri thức nội bộ qua giao diện streaming.

### Tính năng chính

- **Admin**: upload tài liệu (PDF/DOCX/XLSX/TXT), phân quyền level + group, quản lý user
- **User**: landing, đăng ký/đăng nhập, chat UI streaming (SSE), citation, debug chunks
- **RAG**: LiteLLM multi-provider, Qdrant vector store với ACL filter, reranker, chống prompt injection

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Celery |
| RAG | LiteLLM, Qdrant, LangChain text splitter |
| Frontend | Next.js 14, TypeScript, TailwindCSS, shadcn/ui, Zustand |
| Infra | PostgreSQL 16, Qdrant, Redis, MinIO, Docker Compose |

---

## Cấu trúc repository

```
BoostRAG/
├── README.md
├── docker-compose.yml
├── Makefile / tasks.ps1
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP routes
│   │   ├── core/         # Config, security, deps
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── schemas/      # Pydantic DTOs
│   │   ├── services/     # Business logic
│   │   ├── rag/          # Ingestion + retrieval + LLM
│   │   └── workers/      # Celery tasks
│   ├── alembic/
│   └── tests/
└── frontend/
    ├── app/              # Next.js App Router pages
    ├── components/
    └── lib/              # API client, auth, utils
```

---

## Quick start

```bash
# 1. Cấu hình env (copy template local, chỉnh API keys)
cp .env.example .env

# 2. Khởi động infra
docker compose up -d postgres qdrant redis minio

# 3. Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1 | Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.scripts.seed_admin
uvicorn app.main:app --reload --port 8000

# 4. Frontend (terminal khác)
cd frontend
pnpm install
pnpm dev                    # http://localhost:3000

# 5. Worker (terminal khác)
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

Hoặc chạy toàn bộ stack: `docker compose up -d` (hoặc `make up` / `./tasks.ps1 up`).

> Admin mặc định: `admin@boostrag.local` / password từ env `SEED_ADMIN_PASSWORD`. Đổi password ngay sau lần đăng nhập đầu.

---

## Roadmap

- [x] Phase 0: Repo setup, Docker Compose
- [x] Phase 1: Auth, RBAC, Landing, Login/Register UI
- [x] Phase 2: Document ingestion + Admin doc management
- [ ] Phase 3: RAG engine + Chat UI + Streaming
- [ ] Phase 4: Guardrails + Function calling
- [ ] Phase 5: Debug panel + Admin debug console
- [ ] Phase 6: Multi-provider model switching
- [ ] Phase 7: Polish, citation, error handling

---

## License

MIT
