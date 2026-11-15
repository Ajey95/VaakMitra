"""Global search router — one endpoint the top-bar search box calls.

Searches across lessons, videos, games, quizzes and (for admins) users, and
returns a small mixed result set grouped by type.
"""
from fastapi import APIRouter, Depends, Query
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def global_search(q: str = Query(min_length=1), current_user: dict = Depends(get_current_user)):
    """Mixed-type search across content collections."""
    db = get_database()
    rx = {"$regex": q, "$options": "i"}
    results = {}

    results["videos"] = serialize(await db.videos.find(
        {"active": True, "$or": [{"title": rx}, {"description": rx}]}
    ).limit(10).to_list(length=10))
    results["games"] = serialize(await db.games.find(
        {"active": True, "$or": [{"title": rx}, {"description": rx}]}
    ).limit(10).to_list(length=10))
    results["quizzes"] = serialize(await db.quizzes.find(
        {"active": True, "$or": [{"title": rx}, {"description": rx}]}
    ).limit(10).to_list(length=10))
    results["announcements"] = serialize(await db.announcements.find(
        {"published": True, "$or": [{"title": rx}, {"body": rx}]}
    ).limit(10).to_list(length=10))

    if current_user.get("role") == "admin":
        users = await db.users.find(
            {"$or": [{"full_name": rx}, {"email": rx}, {"child_name": rx}]}
        ).limit(10).to_list(length=10)
        results["users"] = serialize(users)

    total = sum(len(v) for v in results.values())
    return {"query": q, "total": total, "results": results}


@router.get("/suggest")
async def suggest(q: str = Query(min_length=1), current_user: dict = Depends(get_current_user)):
    """Lightweight title-only suggestions for an autocomplete dropdown."""
    db = get_database()
    rx = {"$regex": q, "$options": "i"}
    titles = []
    for coll in ("videos", "games", "quizzes"):
        rows = await db[coll].find({"title": rx}, {"title": 1}).limit(5).to_list(length=5)
        titles += [r["title"] for r in rows]
    return {"suggestions": titles[:10]}
