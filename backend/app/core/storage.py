"""MinIO storage client helper — upload, download, delete prefix."""

from __future__ import annotations

import io
from typing import Protocol, runtime_checkable

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class StorageClient(Protocol):
    """Protocol for object storage operations."""

    def upload(self, key: str, data: bytes, content_type: str) -> str: ...
    def download(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...


class MinioStorage:
    """MinIO/S3-compatible storage client."""

    def __init__(self) -> None:
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        self._bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info("storage.upload", key=key, size=len(data))
        return key

    def download(self, key: str) -> bytes:
        try:
            response = self._client.get_object(self._bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                raise NotFoundError(
                    "File not found in storage",
                    details={"key": key},
                ) from exc
            raise

    def delete_prefix(self, prefix: str) -> None:
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=True)
        keys = [obj.object_name for obj in objects if obj.object_name]
        if not keys:
            return
        from minio.deleteobjects import DeleteObject

        errors = list(
            self._client.remove_objects(
                self._bucket,
                [DeleteObject(k) for k in keys],
            ),
        )
        for err in errors:
            logger.warning("storage.delete_error", error=str(err))
        logger.info("storage.delete_prefix", prefix=prefix, count=len(keys))


class InMemoryStorage:
    """In-memory storage for tests."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        del content_type
        self._objects[key] = data
        return key

    def download(self, key: str) -> bytes:
        if key not in self._objects:
            raise NotFoundError("File not found in storage", details={"key": key})
        return self._objects[key]

    def delete_prefix(self, prefix: str) -> None:
        to_delete = [k for k in self._objects if k.startswith(prefix)]
        for k in to_delete:
            del self._objects[k]


def build_document_storage_key(document_id: str, original_filename: str) -> str:
    """Build MinIO key: documents/{id}/original.{ext}."""
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "bin"
    return f"documents/{document_id}/original.{ext}"


def get_storage_client(*, in_memory: bool = False) -> StorageClient:
    """Factory for storage client."""
    if in_memory or settings.is_test():
        return InMemoryStorage()
    return MinioStorage()
