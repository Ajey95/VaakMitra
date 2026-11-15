"""Therapist portal: provision accounts, assign children, view their progress.

Children (the existing parent/child user accounts) are linked to a therapist via
a `therapist_id` field on the user document. Therapists only ever see children
assigned to them; admins may see any.
"""
from datetime import datetime, timezone

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from ..config import settings
from ..database import get_database
from ..utils.jwt_handler import (
    create_access_token, get_current_user, require_therapist,
)
from ..utils.mongo import audit
from .analysis import summarize_evaluations


router = APIRouter(prefix="/api/therapist", tags=["therapist"])


class TherapistCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=8)


class AssignRequest(BaseModel):
    child_email: EmailStr


async def _build_child_rollup(db, child: dict) -> dict:
    """Summarize a single child's progress for the therapist list/detail views."""
    child_id = str(child["_id"])
    evaluations = await db.evaluations.find(
        {"user_id": child_id}
    ).sort("created_at", -1).limit(200).to_list(length=200)
    analysis = summarize_evaluations(evaluations)
    progress_docs = await db.progress.find({"user_id": child_id}).to_list(length=100)
    completed = len([p for p in progress_docs if p.get("completed")])
    last_active = None
    if evaluations:
        created = evaluations[0].get("created_at")
        last_active = created.isoformat() if hasattr(created, "isoformat") else None

    return {
        "id": child_id,
        "child_name": child.get("child_name"),
        "full_name": child.get("full_name"),
        "child_age": child.get("child_age"),
        "email": child.get("email"),
        "total_stars": child.get("total_stars", 0),
        "total_sessions": child.get("total_sessions", 0),
        "avg_accuracy": analysis["overall"],
        "completed_lessons": completed,
        "weakest": analysis["weakest"],
        "last_active": last_active,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_therapist(data: TherapistCreate, response: Response):
    """Create a therapist account (no child profile)."""
    db = get_database()
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = {
        "email": data.email,
        "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(),
        "full_name": data.full_name,
        "child_name": None,
        "child_age": None,
        "language": "Tamil",
        "role": "therapist",
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
        "total_sessions": 0,
        "total_stars": 0,
    }
    await db.users.insert_one(doc)
    token = create_access_token(data={"sub": data.email, "role": "therapist"})
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    return {
        "message": "Therapist account created",
        "access_token": token,
        "token_type": "bearer",
        "user": {"email": data.email, "full_name": data.full_name, "role": "therapist"},
    }


@router.get("/children")
async def list_children(current_user: dict = Depends(require_therapist)):
    """List children assigned to the current therapist, with progress rollups."""
    db = get_database()
    therapist_id = str(current_user["_id"])
    query = {} if current_user.get("role") == "admin" else {"therapist_id": therapist_id}
    query["role"] = "user"
    children = await db.users.find(query).to_list(length=200)
    rollups = [await _build_child_rollup(db, c) for c in children]
    rollups.sort(key=lambda r: r["avg_accuracy"])  # neediest first
    return {"children": rollups, "count": len(rollups)}


@router.post("/assign", status_code=status.HTTP_201_CREATED)
async def assign_child(data: AssignRequest, current_user: dict = Depends(require_therapist)):
    """Assign an existing child account to the current therapist by email."""
    if current_user.get("role") != "therapist":
        raise HTTPException(status_code=403, detail="therapist_account_required")
    db = get_database()
    child = await db.users.find_one({"email": data.child_email, "role": "user"})
    if not child:
        raise HTTPException(status_code=404, detail="No child account with that email")
    existing = child.get("therapist_id")
    if existing:
        raise HTTPException(status_code=409, detail="Child already assigned; an administrator must review reassignment")
    assigned_at = datetime.now(timezone.utc)
    result = await db.users.update_one(
        {"_id": child["_id"], "therapist_id": {"$exists": False}},
        {"$set": {"therapist_id": str(current_user["_id"]),
                  "therapist_assigned_at": assigned_at}},
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=409, detail="Child assignment changed")
    await audit("therapist.child_assigned", current_user, target=str(child["_id"]))
    return {"message": f"Assigned {child.get('child_name') or child['email']}"}


@router.get("/children/{child_id}")
async def child_detail(child_id: str, current_user: dict = Depends(require_therapist)):
    """Full progress + analytics for one assigned child."""
    db = get_database()
    if not ObjectId.is_valid(child_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    child = await db.users.find_one({"_id": ObjectId(child_id)})
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if (current_user.get("role") != "admin"
            and child.get("therapist_id") != str(current_user["_id"])):
        raise HTTPException(status_code=403, detail="Not your assigned child")

    rollup = await _build_child_rollup(db, child)
    evaluations = await db.evaluations.find(
        {"user_id": child_id}
    ).sort("created_at", -1).limit(200).to_list(length=200)
    analysis = summarize_evaluations(evaluations)
    return {"child": rollup, "analysis": analysis}


@router.delete("/children/{child_id}")
async def unassign_child(child_id: str, current_user: dict = Depends(require_therapist)):
    """Remove the therapist link from a child."""
    db = get_database()
    if not ObjectId.is_valid(child_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    await db.users.update_one(
        {"_id": ObjectId(child_id), "therapist_id": str(current_user["_id"])},
        {"$unset": {"therapist_id": "", "therapist_assigned_at": ""}},
    )
    await audit("therapist.child_unassigned", current_user, target=child_id)
    return {"message": "Child unassigned"}
