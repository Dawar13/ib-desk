"""Object storage abstraction.

Two backends sit behind one interface, selected by configuration:
  - LocalStorage writes to a filesystem directory. Used by tests and CI, so the
    hard gates need no external secret.
  - SupabaseStorage uses the Supabase Storage REST API. Used in deployed
    environments.

The interface stores an object under an opaque key and reads it back. Retrieval
returns the bytes; the API layer derives the content type from the document's
source kind, so the storage layer does not need to track it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...

    async def get(self, key: str) -> bytes: ...

    async def exists(self, key: str) -> bool: ...


class LocalStorage:
    """Filesystem backend. Keys are flattened so they cannot escape the root."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_")
        return self._root / safe

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        self._path(key).write_bytes(data)
        return key

    async def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()


class SupabaseStorage:
    """Supabase Storage REST backend. Used only in deployed environments."""

    def __init__(self, base_url: str, service_role_key: str, bucket: str) -> None:
        self._base = base_url.rstrip("/")
        self._key = service_role_key
        self._bucket = bucket

    def _object_url(self, key: str) -> str:
        return f"{self._base}/storage/v1/object/{self._bucket}/{key}"

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        import httpx

        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self._object_url(key), content=data, headers=headers)
            response.raise_for_status()
        return key

    async def get(self, key: str) -> bytes:
        import httpx

        headers = {"Authorization": f"Bearer {self._key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self._object_url(key), headers=headers)
            response.raise_for_status()
            return response.content

    async def exists(self, key: str) -> bool:
        import httpx

        headers = {"Authorization": f"Bearer {self._key}"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self._object_url(key), headers=headers)
                return response.status_code == 200
        except httpx.HTTPError:
            return False


def build_storage(
    backend: str,
    local_path: str,
    supabase_url: str | None,
    supabase_service_role_key: str | None,
    bucket: str,
) -> Storage:
    """Construct the configured storage backend.

    Defaults to LocalStorage. The supabase backend requires the Supabase URL and
    service role key to be set; it raises a clear error if they are missing.
    """
    if backend == "supabase":
        if not supabase_url or not supabase_service_role_key:
            raise ValueError(
                "STORAGE_BACKEND=supabase requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
            )
        return SupabaseStorage(supabase_url, supabase_service_role_key, bucket)
    return LocalStorage(local_path)


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """Return the configured storage backend, built once from settings."""
    from app.config import get_settings

    settings = get_settings()
    return build_storage(
        settings.storage_backend,
        settings.storage_local_path,
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.storage_bucket,
    )
