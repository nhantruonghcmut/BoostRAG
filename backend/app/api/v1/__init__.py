"""BoostRAG REST API v1.

Tổng hợp các router con thành 1 `APIRouter` (xem `api_router`). Mọi route
prefix `/api/v1/...`.
"""

from fastapi import APIRouter

from app.api.v1 import auth as auth_router, documents as documents_router
from app.api.v1.admin import (
    documents as admin_documents_router,
    users as admin_users_router,
)

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(documents_router.router)
api_router.include_router(admin_users_router.router)
api_router.include_router(admin_documents_router.router)
