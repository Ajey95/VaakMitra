"""Shared MongoDB helpers used across routers.

Centralises the boilerplate that was previously copy-pasted in every router:
ObjectId parsing, JSON-safe serialization (ObjectId -> str, datetime -> ISO),
pagination and a small audit-log writer. Keeping this in one place means every
new module behaves consistently (same pagination envelope, same id handling).
"""
from datetime import datetime
from typing import Any, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from ..database import get_database


def oid(value: str) -> ObjectId:
    """Parse a string into an ObjectId or raise a 400."""
    if isinstance(value, ObjectId):
        return value
    if not value or not ObjectId.is_valid(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id")
    return ObjectId(value)


def _clean(value: Any) -> Any:
    """Recursively convert Mongo/BSON types into JSON-safe values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    return value


def serialize(doc: Any) -> Any:
    """Serialize a Mongo document (or list) into a JSON-safe dict.

    Adds a convenience ``id`` mirror of ``_id`` and always strips secrets.
    """
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize(d) for d in doc]
    out = {k: _clean(v) for k, v in doc.items()}
    if "_id" in out:
        out["id"] = out["_id"]
    out.pop("password_hash", None)
    out.pop("otp_hash", None)
    return out


async def paginate(
    collection,
    query: dict,
    page: int = 1,
    limit: int = 20,
    sort_field: str = "created_at",
    sort_dir: int = -1,
) -> dict:
    """Return a standard paginated envelope for any collection query."""
    page = max(1, int(page or 1))
    limit = max(1, min(int(limit or 20), 100))
    total = await collection.count_documents(query)
    skip = (page - 1) * limit
    items = (
        await collection.find(query)
        .sort(sort_field, sort_dir)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    return {
        "items": serialize(items),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


async def audit(action: str, actor: Optional[dict] = None, target: Optional[str] = None, meta: Optional[dict] = None) -> None:
    """Write a row to the audit_logs collection. Never raises."""
    try:
        db = get_database()
        await db.audit_logs.insert_one({
            "action": action,
            "actor_id": str(actor["_id"]) if actor and actor.get("_id") else None,
            "actor_email": actor.get("email") if actor else None,
            "actor_role": actor.get("role") if actor else None,
            "target": target,
            "meta": meta or {},
            "created_at": datetime.utcnow(),
        })
    except Exception:
        # Auditing must never break the primary request.
        pass


def now() -> datetime:
    """UTC now — single source so tests can monkeypatch if needed."""
    return datetime.utcnow()
