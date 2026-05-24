"""Celery worker tasks.

Phase 1 chỉ setup Celery app — ingestion tasks sẽ thêm ở Phase 2
(`ingestion_tasks.py`). Tasks idempotent, nhận id arg (không pass object lớn).
"""
