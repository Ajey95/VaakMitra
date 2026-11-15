"""Content router — blog posts & tips feed.

Backs the About/landing content feed. Admins publish articles/tips; all users
read the published feed and can like posts.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/content", tags=["content"])

TYPES = ["blog", "tip", "story", "guide"]


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    type: str = "blog"
    tags: List[str] = []
    cover_image: Optional[str] = None
    published: bool = True


class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image: Optional[str] = None
    published: Optional[bool] = None


@router.get("")
async def list_posts(page: int = 1, limit: int = 12, type: Optional[str] = None, tag: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Published content feed."""
    db = get_database()
    query = {"published": True}
    if type in TYPES:
        query["type"] = type
    if tag:
        query["tags"] = tag
    return await paginate(db.content_posts, query, page, limit)


@router.get("/tags")
async def list_tags(current_user: dict = Depends(get_current_user)):
    """Distinct tags across published posts."""
    db = get_database()
    tags = await db.content_posts.distinct("tags", {"published": True})
    return {"tags": sorted(t for t in tags if t)}


@router.get("/{post_id}")
async def get_post(post_id: str, current_user: dict = Depends(get_current_user)):
    """Read a post and increment views."""
    db = get_database()
    post = await db.content_posts.find_one({"_id": oid(post_id)})
    if not post or not post.get("published"):
        raise HTTPException(status_code=404, detail="Post not found")
    await db.content_posts.update_one({"_id": oid(post_id)}, {"$inc": {"views": 1}})
    return serialize(post)


@router.post("/{post_id}/like")
async def like_post(post_id: str, current_user: dict = Depends(get_current_user)):
    """Toggle a like on a post."""
    db = get_database()
    uid = str(current_user["_id"])
    existing = await db.content_likes.find_one({"user_id": uid, "post_id": post_id})
    if existing:
        await db.content_likes.delete_one({"_id": existing["_id"]})
        await db.content_posts.update_one({"_id": oid(post_id)}, {"$inc": {"likes": -1}})
        return {"liked": False}
    await db.content_likes.insert_one({"user_id": uid, "post_id": post_id, "created_at": now()})
    await db.content_posts.update_one({"_id": oid(post_id)}, {"$inc": {"likes": 1}})
    return {"liked": True}


# ---- Admin CRUD ---------------------------------------------------------------

@router.post("/admin")
async def create_post(payload: PostCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a post."""
    db = get_database()
    doc = {**payload.model_dump(), "author": current_admin.get("full_name"), "views": 0, "likes": 0, "created_at": now(), "updated_at": now()}
    result = await db.content_posts.insert_one(doc)
    await audit("content.create", current_admin, target=str(result.inserted_id))
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/admin/all")
async def admin_all(page: int = 1, limit: int = 30, current_admin: dict = Depends(require_admin)):
    """Admin: list all posts incl. drafts."""
    db = get_database()
    return await paginate(db.content_posts, {}, page, limit)


@router.patch("/admin/{post_id}")
async def update_post(post_id: str, payload: PostUpdate, current_admin: dict = Depends(require_admin)):
    """Admin: update a post."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    updates["updated_at"] = now()
    result = await db.content_posts.update_one({"_id": oid(post_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return serialize(await db.content_posts.find_one({"_id": oid(post_id)}))


@router.delete("/admin/{post_id}")
async def delete_post(post_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a post."""
    db = get_database()
    result = await db.content_posts.delete_one({"_id": oid(post_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    await audit("content.delete", current_admin, target=post_id)
    return {"message": "Deleted"}
