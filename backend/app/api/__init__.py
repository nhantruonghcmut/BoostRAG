"""HTTP API layer (FastAPI routers).

Mỗi version có sub-package riêng (vd `app.api.v1`). Mọi route phải đi qua
service layer — KHÔNG truy DB trực tiếp ở đây.
"""
