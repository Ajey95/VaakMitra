"""Parent extras — multi-child management, monthly reports, milestones.

Extends the parent router. A parent account can manage several children; each
child is a linked user document with ``parent_id`` set.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta
import bcrypt
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/parent", tags=["parent-ext"])


class ChildCreate(BaseModel):
    child_name: str = Field(min_length=1, max_length=120)
    child_age: int = Field(ge=2, le=18)
    language: str = "Tamil"
    email: Optional[str] = None
    password: Optional[str] = None


@router.get("/children")
async def list_children(current_user: dict = Depends(get_current_user)):
    """List children linked to this parent (plus the parent's own child profile)."""
    db = get_database()
    uid = str(current_user["_id"])
    children = await db.users.find({"parent_id": uid}).to_list(length=100)
    out = serialize(children)
    for c in out:
        c["sessions"] = await db.evaluations.count_documents({"user_id": c["id"]})
    return {"children": out}


@router.post("/children")
async def add_child(payload: ChildCreate, current_user: dict = Depends(get_current_user)):
    """Add a child profile under this parent."""
    db = get_database()
    email = payload.email or f"child_{now().strftime('%Y%m%d%H%M%S')}@speakeasy.local"
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already used")
    pw = payload.password or "child1234"
    doc = {
        "email": email, "password_hash": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
        "full_name": current_user.get("full_name"), "child_name": payload.child_name,
        "child_age": payload.child_age, "language": payload.language, "role": "user",
        "parent_id": str(current_user["_id"]), "created_at": now(), "last_login": None,
        "total_sessions": 0, "total_stars": 0,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/children/{child_id}")
async def remove_child(child_id: str, current_user: dict = Depends(get_current_user)):
    """Unlink (delete) a child profile owned by this parent."""
    db = get_database()
    child = await db.users.find_one({"_id": oid(child_id), "parent_id": str(current_user["_id"])})
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    await db.users.delete_one({"_id": oid(child_id)})
    await db.evaluations.delete_many({"user_id": child_id})
    await db.progress.delete_many({"user_id": child_id})
    return {"message": "Child removed"}


@router.get("/monthly/{child_id}")
async def monthly_report(child_id: str, current_user: dict = Depends(get_current_user)):
    """This-month vs last-month report for a child."""
    db = get_database()
    child = await db.users.find_one({"_id": oid(child_id)})
    if not child or (str(child.get("parent_id")) != str(current_user["_id"]) and str(child["_id"]) != str(current_user["_id"])):
        raise HTTPException(status_code=403, detail="Access denied")
    month_start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (month_start - timedelta(days=1)).replace(day=1)

    async def stats(start, end):
        evals = await db.evaluations.find({"user_id": child_id, "created_at": {"$gte": start, "$lt": end}}, {"accuracy": 1}).to_list(length=100000)
        return {"sessions": len(evals), "avg_accuracy": round(sum(e.get("accuracy", 0) for e in evals) / len(evals), 1) if evals else 0}

    this_month = await stats(month_start, now() + timedelta(days=1))
    last_month = await stats(prev_start, month_start)
    return {"child_id": child_id, "this_month": this_month, "last_month": last_month}


@router.get("/milestones/{child_id}")
async def milestones(child_id: str, current_user: dict = Depends(get_current_user)):
    """Derived milestone list (first session, 10 sessions, 90%+ accuracy, etc.)."""
    db = get_database()
    child = await db.users.find_one({"_id": oid(child_id)})
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    sessions = child.get("total_sessions", 0)
    stars = child.get("total_stars", 0)
    high = await db.evaluations.count_documents({"user_id": child_id, "accuracy": {"$gte": 90}})
    ms = [
        {"label": "First session completed", "achieved": sessions >= 1},
        {"label": "10 sessions completed", "achieved": sessions >= 10},
        {"label": "Earned 20 stars", "achieved": stars >= 20},
        {"label": "First 90%+ pronunciation", "achieved": high >= 1},
        {"label": "5 high-accuracy sessions", "achieved": high >= 5},
    ]
    return {"child_id": child_id, "milestones": ms, "achieved_count": sum(1 for m in ms if m["achieved"])}
