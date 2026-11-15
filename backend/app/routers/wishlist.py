"""Wishlist & suggestions router.

Backs the app "Tell us your wishlist" and "Suggest a place/lesson" flows. Users
save lessons/videos to a wishlist and submit content suggestions for the team.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/wishlist", tags=["wishlist"])


class WishlistItem(BaseModel):
    item_type: str = Field(description="lesson | video | game | quiz")
    item_ref: str
    title: Optional[str] = None


class Suggestion(BaseModel):
    kind: str = "lesson"       # lesson | word | feature | place
    title: str = Field(min_length=1, max_length=200)
    detail: Optional[str] = Field(default=None, max_length=2000)


@router.post("")
async def add_item(payload: WishlistItem, current_user: dict = Depends(get_current_user)):
    """Add an item to the wishlist (dedup per user+item)."""
    db = get_database()
    uid = str(current_user["_id"])
    if await db.wishlist.find_one({"user_id": uid, "item_ref": payload.item_ref, "item_type": payload.item_type}):
        raise HTTPException(status_code=409, detail="Already in wishlist")
    doc = {"user_id": uid, **payload.model_dump(), "created_at": now()}
    result = await db.wishlist.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def list_items(current_user: dict = Depends(get_current_user)):
    """List the caller's wishlist."""
    db = get_database()
    rows = await db.wishlist.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).to_list(length=500)
    return {"items": serialize(rows), "count": len(rows)}


@router.delete("/{item_id}")
async def remove_item(item_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a wishlist item."""
    db = get_database()
    result = await db.wishlist.delete_one({"_id": oid(item_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Removed"}


# ---- Suggestions --------------------------------------------------------------

@router.post("/suggest")
async def suggest(payload: Suggestion, current_user: dict = Depends(get_current_user)):
    """Submit a content/feature suggestion."""
    db = get_database()
    doc = {
        "user_id": str(current_user["_id"]), "user_name": current_user.get("full_name"),
        **payload.model_dump(), "votes": 0, "status": "submitted", "created_at": now(),
    }
    result = await db.suggestions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/suggestions")
async def list_suggestions(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Public list of suggestions (most-voted first)."""
    db = get_database()
    return await paginate(db.suggestions, {}, page, limit, sort_field="votes", sort_dir=-1)


@router.post("/suggestions/{suggestion_id}/vote")
async def vote_suggestion(suggestion_id: str, current_user: dict = Depends(get_current_user)):
    """Upvote a suggestion (one vote per user)."""
    db = get_database()
    uid = str(current_user["_id"])
    if await db.suggestion_votes.find_one({"user_id": uid, "suggestion_id": suggestion_id}):
        raise HTTPException(status_code=409, detail="Already voted")
    await db.suggestion_votes.insert_one({"user_id": uid, "suggestion_id": suggestion_id, "created_at": now()})
    await db.suggestions.update_one({"_id": oid(suggestion_id)}, {"$inc": {"votes": 1}})
    return {"message": "Voted"}


@router.get("/suggestions/admin/all")
async def admin_suggestions(page: int = 1, limit: int = 30, current_admin: dict = Depends(require_admin)):
    """Admin: review all suggestions."""
    db = get_database()
    return await paginate(db.suggestions, {}, page, limit, sort_field="votes", sort_dir=-1)
