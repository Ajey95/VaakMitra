"""Video library router — learning videos with per-user watch progress.

Backs the Videos page. Videos are categorised (vowels, consonants, words, tips);
users track watch progress and completion; admins manage the catalog.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/videos", tags=["videos"])

CATEGORIES = ["vowels", "consonants", "words", "tips", "stories", "exercises"]

DEFAULT_VIDEOS = [
    {"slug": "vowel-a", "title": "Learn அ", "category": "vowels", "duration_sec": 120, "url": "", "thumbnail": "", "description": "How to pronounce அ."},
    {"slug": "vowel-aa", "title": "Learn ஆ", "category": "vowels", "duration_sec": 130, "url": "", "thumbnail": "", "description": "How to pronounce ஆ."},
    {"slug": "word-amma", "title": "Say அம்மா", "category": "words", "duration_sec": 90, "url": "", "thumbnail": "", "description": "Practise the word அம்மா."},
    {"slug": "tip-breathing", "title": "Breathing Tips", "category": "tips", "duration_sec": 200, "url": "", "thumbnail": "", "description": "Airflow control for clearer speech."},
]


class WatchProgress(BaseModel):
    position_sec: int = Field(ge=0)
    completed: bool = False


class VideoCreate(BaseModel):
    slug: str
    title: str
    category: str = "tips"
    duration_sec: int = 0
    url: str = ""
    thumbnail: str = ""
    description: str = ""
    active: bool = True


async def _ensure_seeded():
    db = get_database()
    if await db.videos.count_documents({}) == 0:
        await db.videos.insert_many([{**v, "active": True, "views": 0, "created_at": now()} for v in DEFAULT_VIDEOS])


@router.get("")
async def list_videos(category: Optional[str] = None, page: int = 1, limit: int = 30, current_user: dict = Depends(get_current_user)):
    """List videos, annotated with the caller's watch progress."""
    await _ensure_seeded()
    db = get_database()
    query = {"active": True}
    if category in CATEGORIES:
        query["category"] = category
    result = await paginate(db.videos, query, page, limit, sort_field="created_at", sort_dir=1)
    progress = {p["video_slug"]: p for p in await db.video_progress.find({"user_id": str(current_user["_id"])}).to_list(length=1000)}
    for v in result["items"]:
        p = progress.get(v["slug"])
        v["watch_position"] = p["position_sec"] if p else 0
        v["completed"] = p["completed"] if p else False
    return result


@router.get("/categories")
async def categories(current_user: dict = Depends(get_current_user)):
    """List categories with video counts."""
    await _ensure_seeded()
    db = get_database()
    out = []
    for c in CATEGORIES:
        count = await db.videos.count_documents({"category": c, "active": True})
        out.append({"category": c, "count": count})
    return {"categories": out}


@router.get("/{video_slug}")
async def get_video(video_slug: str, current_user: dict = Depends(get_current_user)):
    """Video detail (increments view count) with the caller's progress."""
    db = get_database()
    video = await db.videos.find_one({"slug": video_slug, "active": True})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.videos.update_one({"slug": video_slug}, {"$inc": {"views": 1}})
    p = await db.video_progress.find_one({"user_id": str(current_user["_id"]), "video_slug": video_slug})
    out = serialize(video)
    out["watch_position"] = p["position_sec"] if p else 0
    out["completed"] = p["completed"] if p else False
    return out


@router.post("/{video_slug}/progress")
async def save_progress(video_slug: str, payload: WatchProgress, current_user: dict = Depends(get_current_user)):
    """Upsert watch progress; award coins the first time a video is completed."""
    db = get_database()
    uid = str(current_user["_id"])
    video = await db.videos.find_one({"slug": video_slug})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    existing = await db.video_progress.find_one({"user_id": uid, "video_slug": video_slug})
    newly_completed = payload.completed and not (existing and existing.get("completed"))
    await db.video_progress.update_one(
        {"user_id": uid, "video_slug": video_slug},
        {"$set": {"position_sec": payload.position_sec, "completed": payload.completed, "updated_at": now()},
         "$setOnInsert": {"created_at": now()}},
        upsert=True,
    )
    coins = 0
    if newly_completed:
        coins = 15
        from .wallet import credit_wallet
        await credit_wallet(uid, coins=coins, reason=f"Watched {video.get('title')}")
    return {"message": "Progress saved", "coins_awarded": coins}


# ---- Admin --------------------------------------------------------------------

@router.post("/admin")
async def create_video(payload: VideoCreate, current_admin: dict = Depends(require_admin)):
    """Admin: add a video."""
    db = get_database()
    if await db.videos.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Slug exists")
    doc = {**payload.model_dump(), "views": 0, "created_at": now()}
    result = await db.videos.insert_one(doc)
    await audit("video.create", current_admin, target=payload.slug)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.patch("/admin/{video_slug}")
async def update_video(video_slug: str, payload: dict, current_admin: dict = Depends(require_admin)):
    """Admin: update a video."""
    db = get_database()
    payload.pop("_id", None)
    result = await db.videos.update_one({"slug": video_slug}, {"$set": payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    return serialize(await db.videos.find_one({"slug": video_slug}))


@router.delete("/admin/{video_slug}")
async def delete_video(video_slug: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a video."""
    db = get_database()
    result = await db.videos.delete_one({"slug": video_slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"message": "Deleted"}
