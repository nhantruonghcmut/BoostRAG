"""Cross-cutting concerns: config, logging, security, exceptions, DI.

Mọi layer khác (api/services/rag/workers) đều có thể import từ `app.core`.
Module này KHÔNG được phụ thuộc ngược lên bất cứ layer nào.
"""
