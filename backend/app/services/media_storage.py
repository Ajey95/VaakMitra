"""Durable media storage adapters.

Render's instance filesystem is ephemeral, so production uploads are stored in
Cloudinary. Local disk remains available for development and automated tests.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

from fastapi.concurrency import run_in_threadpool

from ..config import settings


class MediaStorage:
    async def save(self, data: bytes, filename: str, content_type: str, user_id: str, purpose: str) -> dict[str, Any]:
        raise NotImplementedError

    async def delete(self, record: dict[str, Any]) -> None:
        raise NotImplementedError


class LocalMediaStorage(MediaStorage):
    def __init__(self, directory: str | None = None):
        self.directory = Path(directory or (Path.cwd() / "uploads"))

    async def save(self, data: bytes, filename: str, content_type: str, user_id: str, purpose: str) -> dict[str, Any]:
        self.directory.mkdir(parents=True, exist_ok=True)
        extension = Path(filename or "").suffix[:10]
        stored_name = f"{secrets.token_hex(12)}{extension}"
        (self.directory / stored_name).write_bytes(data)
        return {"storage": "local", "stored_name": stored_name, "url": f"/uploads/{stored_name}"}

    async def delete(self, record: dict[str, Any]) -> None:
        stored_name = record.get("stored_name")
        if stored_name:
            try:
                (self.directory / stored_name).unlink()
            except FileNotFoundError:
                pass


class CloudinaryMediaStorage(MediaStorage):
    def __init__(self):
        import cloudinary

        self._cloudinary = cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    async def save(self, data: bytes, filename: str, content_type: str, user_id: str, purpose: str) -> dict[str, Any]:
        import cloudinary.uploader

        result = await run_in_threadpool(
            cloudinary.uploader.upload,
            data,
            resource_type="auto",
            folder=f"speakeasy/{purpose or 'general'}",
            public_id=f"{user_id}-{secrets.token_hex(8)}",
            use_filename=False,
            unique_filename=False,
            overwrite=False,
        )
        return {
            "storage": "cloudinary",
            "stored_name": result.get("public_id"),
            "public_id": result.get("public_id"),
            "resource_type": result.get("resource_type", "image"),
            "url": result.get("secure_url") or result.get("url"),
        }

    async def delete(self, record: dict[str, Any]) -> None:
        import cloudinary.uploader

        public_id = record.get("public_id") or record.get("stored_name")
        if public_id:
            await run_in_threadpool(
                cloudinary.uploader.destroy,
                public_id,
                resource_type=record.get("resource_type", "image"),
                invalidate=True,
            )


def get_media_storage() -> MediaStorage:
    if settings.cloudinary_enabled:
        return CloudinaryMediaStorage()
    if settings.APP_ENV in {"production", "prod"}:
        raise RuntimeError("Cloudinary credentials are required for production uploads")
    return LocalMediaStorage()
