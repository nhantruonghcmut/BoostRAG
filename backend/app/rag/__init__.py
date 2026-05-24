"""RAG pipeline (ingestion + retrieval + LLM + guardrails + tools + engine).

**Quan trọng:** module này KHÔNG import từ `app.services` hoặc `app.api`.
Service layer truyền data vào RAG qua argument. Xem `docs/RAG_PIPELINE.md`
+ `docs/MODULES.md`.

Phase 1 chỉ tạo skeleton sub-packages — implementation thực hiện ở Phase 2-3.
"""
