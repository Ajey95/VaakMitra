"""Bookmarks router — save content for quick access.

Distinct from wishlist (a 'want to do' queue); bookmarks are a personal
'saved/favourites' set across any content type.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


class BookmarkCreate(BaseModel):
    target_type: str = Field(description="lesson | video | game | post")
    target_ref: str
    title: Optional[str] = None


@router.post("")
async def add_bookmark(payload: BookmarkCreate, current_user: dict = Depends(get_current_user)):
    """Add a bookmark (dedup per user+target)."""
    db = get_database()
    uid = str(current_user["_id"])
    if await db.bookmarks.find_one({"user_id": uid, "target_type": payload.target_type, "target_ref": payload.target_ref}):
        raise HTTPException(status_code=409, detail="Already bookmarked")
    doc = {"user_id": uid, **payload.model_dump(), "created_at": now()}
    result = await db.bookmarks.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def list_bookmarks(target_type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List the caller's bookmarks."""
    db = get_database()
    query = {"user_id": str(current_user["_id"])}
    if target_type:
        query["target_type"] = target_type
    rows = await db.bookmarks.find(query).sort("created_at", -1).to_list(length=500)
    return {"bookmarks": serialize(rows), "count": len(rows)}


@router.delete("/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a bookmark."""
    db = get_database()
    result = await db.bookmarks.delete_one({"_id": oid(bookmark_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Removed"}
