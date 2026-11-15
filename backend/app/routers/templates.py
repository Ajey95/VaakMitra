"""Templates router — admin-managed message/email/notification templates.

Admins create reusable templates with ``{{placeholders}}`` used when sending
notifications, emails or announcements from the panel.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import re
from ..database import get_database
from ..utils.jwt_handler import require_admin, get_current_user
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/templates", tags=["templates"])

CHANNELS = ["notification", "email", "whatsapp", "announcement"]


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    channel: str = "notification"
    subject: Optional[str] = None
    body: str = Field(min_length=1)


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class RenderRequest(BaseModel):
    variables: dict = {}


def _placeholders(body: str) -> List[str]:
    return sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", body)))


@router.get("")
async def list_templates(channel: Optional[str] = None, current_admin: dict = Depends(require_admin)):
    """Admin: list templates."""
    db = get_database()
    query = {"channel": channel} if channel in CHANNELS else {}
    rows = await db.templates.find(query).sort("created_at", -1).to_list(length=200)
    return {"templates": serialize(rows)}


@router.post("")
async def create_template(payload: TemplateCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a template."""
    db = get_database()
    doc = {**payload.model_dump(), "placeholders": _placeholders(payload.body),
           "author": current_admin.get("full_name"), "created_at": now(), "updated_at": now()}
    result = await db.templates.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/{template_id}")
async def get_template(template_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: fetch a template."""
    db = get_database()
    doc = await db.templates.find_one({"_id": oid(template_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return serialize(doc)


@router.patch("/{template_id}")
async def update_template(template_id: str, payload: TemplateUpdate, current_admin: dict = Depends(require_admin)):
    """Admin: update a template (recomputes placeholders)."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    if "body" in updates:
        updates["placeholders"] = _placeholders(updates["body"])
    updates["updated_at"] = now()
    result = await db.templates.update_one({"_id": oid(template_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return serialize(await db.templates.find_one({"_id": oid(template_id)}))


@router.post("/{template_id}/render")
async def render_template(template_id: str, payload: RenderRequest, current_admin: dict = Depends(require_admin)):
    """Admin: render a template with variables (preview)."""
    db = get_database()
    doc = await db.templates.find_one({"_id": oid(template_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    body = doc["body"]
    for k, v in payload.variables.items():
        body = re.sub(r"\{\{\s*" + re.escape(k) + r"\s*\}\}", str(v), body)
    return {"rendered": body, "unresolved": _placeholders(body)}


@router.delete("/{template_id}")
async def delete_template(template_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a template."""
    db = get_database()
    result = await db.templates.delete_one({"_id": oid(template_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Deleted"}
