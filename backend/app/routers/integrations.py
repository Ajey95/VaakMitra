"""Integrations router — admin API keys & webhooks (platform extensibility).

Lets admins issue API keys and register outbound webhooks for events (a common
'professional platform' surface). Keys are shown once at creation.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import secrets
import hashlib
from ..database import get_database
from ..utils.jwt_handler import require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

EVENTS = ["user.created", "session.completed", "appointment.booked", "feedback.created", "subscription.created"]


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WebhookCreate(BaseModel):
    url: str
    events: List[str] = Field(default_factory=list)
    active: bool = True


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/api-keys")
async def create_api_key(payload: ApiKeyCreate, current_admin: dict = Depends(require_admin)):
    """Admin: issue an API key (returned once in full)."""
    db = get_database()
    raw = "sk_" + secrets.token_hex(24)
    doc = {"name": payload.name, "key_hash": _hash_key(raw), "prefix": raw[:10],
           "created_by": current_admin.get("email"), "active": True, "last_used": None, "created_at": now()}
    result = await db.api_keys.insert_one(doc)
    await audit("integration.api_key_create", current_admin, target=str(result.inserted_id))
    return {"id": str(result.inserted_id), "api_key": raw, "note": "Store this now — it will not be shown again."}


@router.get("/api-keys")
async def list_api_keys(current_admin: dict = Depends(require_admin)):
    """Admin: list API keys (hashes/prefixes only)."""
    db = get_database()
    rows = await db.api_keys.find({}).sort("created_at", -1).to_list(length=200)
    out = serialize(rows)
    for r in out:
        r.pop("key_hash", None)
    return {"api_keys": out}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: revoke an API key."""
    db = get_database()
    result = await db.api_keys.update_one({"_id": oid(key_id)}, {"$set": {"active": False, "revoked_at": now()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    await audit("integration.api_key_revoke", current_admin, target=key_id)
    return {"message": "Key revoked"}


@router.get("/events")
async def list_events(current_admin: dict = Depends(require_admin)):
    """Admin: list webhook event types."""
    return {"events": EVENTS}


@router.post("/webhooks")
async def create_webhook(payload: WebhookCreate, current_admin: dict = Depends(require_admin)):
    """Admin: register an outbound webhook."""
    db = get_database()
    invalid = [e for e in payload.events if e not in EVENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown events: {invalid}")
    doc = {**payload.model_dump(), "secret": "whsec_" + secrets.token_hex(16), "created_at": now()}
    result = await db.webhooks.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/webhooks")
async def list_webhooks(current_admin: dict = Depends(require_admin)):
    """Admin: list webhooks."""
    db = get_database()
    rows = await db.webhooks.find({}).sort("created_at", -1).to_list(length=200)
    return {"webhooks": serialize(rows)}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a webhook."""
    db = get_database()
    result = await db.webhooks.delete_one({"_id": oid(webhook_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Deleted"}
