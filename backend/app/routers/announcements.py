"""Announcements router — platform-wide news/banners.

Admins publish announcements (news, tips, updates, maintenance). All users read
the live feed; the landing page shows the latest pinned banner.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

TYPES = ["news", "tip", "update", "maintenance", "event"]


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=6000)
    type: str = Field(default="news")
    pinned: bool = False
    published: bool = True
    image_url: Optional[str] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    pinned: Optional[bool] = None
    published: Optional[bool] = None
    image_url: Optional[str] = None


@router.get("")
async def list_live(page: int = 1, limit: int = 20, type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Public (authenticated) feed of published announcements, pinned first."""
    db = get_database()
    query = {"published": True}
    if type in TYPES:
        query["type"] = type
    # Pinned first, then newest — two-key sort via aggregation-free find.
    result = await paginate(db.announcements, query, page, limit, sort_field="created_at", sort_dir=-1)
    result["items"].sort(key=lambda a: (not a.get("pinned", False)))
    return result


@router.get("/banner")
async def latest_banner(current_user: dict = Depends(get_current_user)):
    """Return the single most relevant pinned/live announcement for a banner."""
    db = get_database()
    doc = await db.announcements.find_one({"published": True, "pinned": True}, sort=[("created_at", -1)])
    if not doc:
        doc = await db.announcements.find_one({"published": True}, sort=[("created_at", -1)])
    return serialize(doc)


@router.get("/{announcement_id}")
async def get_one(announcement_id: str, current_user: dict = Depends(get_current_user)):
    """Read a single announcement and bump its view counter."""
    db = get_database()
    doc = await db.announcements.find_one({"_id": oid(announcement_id)})
    if not doc or not doc.get("published"):
        raise HTTPException(status_code=404, detail="Announcement not found")
    await db.announcements.update_one({"_id": oid(announcement_id)}, {"$inc": {"views": 1}})
    return serialize(doc)


# ---- Admin CRUD ---------------------------------------------------------------

@router.post("/admin")
async def create(payload: AnnouncementCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create an announcement."""
    db = get_database()
    doc = {
        **payload.model_dump(),
        "type": payload.type if payload.type in TYPES else "news",
        "author": current_admin.get("full_name"),
        "views": 0,
        "created_at": now(),
        "updated_at": now(),
    }
    result = await db.announcements.insert_one(doc)
    await audit("announcement.create", current_admin, target=str(result.inserted_id))
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/admin/all")
async def admin_all(page: int = 1, limit: int = 30, current_admin: dict = Depends(require_admin)):
    """Admin: list all announcements incl. drafts."""
    db = get_database()
    return await paginate(db.announcements, {}, page, limit)


@router.patch("/admin/{announcement_id}")
async def update(announcement_id: str, payload: AnnouncementUpdate, current_admin: dict = Depends(require_admin)):
    """Admin: update an announcement."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    updates["updated_at"] = now()
    result = await db.announcements.update_one({"_id": oid(announcement_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    await audit("announcement.update", current_admin, target=announcement_id)
    return serialize(await db.announcements.find_one({"_id": oid(announcement_id)}))


@router.delete("/admin/{announcement_id}")
async def delete(announcement_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete an announcement."""
    db = get_database()
    result = await db.announcements.delete_one({"_id": oid(announcement_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    await audit("announcement.delete", current_admin, target=announcement_id)
    return {"message": "Deleted"}
