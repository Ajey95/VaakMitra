"""Therapist extras — session notes & treatment plans.

Extends the therapist router: clinical notes per child and structured treatment
plans with goals/milestones. All endpoints require therapist (or admin) and
enforce that the child is assigned to the therapist.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from ..database import get_database
from ..utils.jwt_handler import require_therapist
from ..utils.mongo import serialize, paginate, oid, now
from ..vaakmitra_word.router import VOCABULARY_REGISTRY
from ..vaakmitra_word.session_limits import SessionLimits

router = APIRouter(prefix="/api/therapist", tags=["therapist-ext"])


class NoteCreate(BaseModel):
    child_id: str
    note: str = Field(min_length=1, max_length=4000)
    tags: List[str] = []


class PlanCreate(BaseModel):
    child_id: str
    title: str
    goals: List[str] = []
    duration_weeks: int = 4
    notes: Optional[str] = None
    word_ids: List[str] = Field(default_factory=list, max_length=25)
    vocabulary_version: Optional[str] = None
    session_limits: SessionLimits = Field(default_factory=SessionLimits)

    @model_validator(mode="after")
    def check_assigned_words(self):
        # DEC-016: a plan may select intended words, but that never activates scoring.
        if not self.word_ids:
            if self.vocabulary_version is not None:
                raise ValueError("vocabulary_version requires assigned words")
            return self
        if self.vocabulary_version != VOCABULARY_REGISTRY.version:
            raise ValueError("vocabulary_version does not match the server registry")
        available = {entry.word_id for entry in VOCABULARY_REGISTRY.entries
                     if entry.kind == "word" and entry.state in ("intended", "active")}
        if len(set(self.word_ids)) != len(self.word_ids) or any(word not in available for word in self.word_ids):
            raise ValueError("word_ids must be unique assigned whole words in the server registry")
        return self


async def _assert_assigned(db, therapist: dict, child_id: str):
    child = await db.users.find_one({"_id": oid(child_id)})
    if not child or child.get("role") != "user":
        raise HTTPException(status_code=404, detail="Child not found")
    if therapist.get("role") != "admin" and str(child.get("therapist_id")) != str(therapist["_id"]):
        raise HTTPException(status_code=403, detail="Child not assigned to you")
    return child


async def _owned_plan(db, therapist, plan_id):
    plan = await db.treatment_plans.find_one({"_id": oid(plan_id)})
    if not plan:
        raise HTTPException(404, detail="Plan not found")
    await _assert_assigned(db, therapist, plan["child_id"])
    if therapist.get("role") != "admin" and plan.get("therapist_id") != str(therapist["_id"]):
        raise HTTPException(403, detail="Plan access denied")
    return plan


@router.post("/notes")
async def add_note(payload: NoteCreate, therapist: dict = Depends(require_therapist)):
    """Add a clinical note for an assigned child."""
    db = get_database()
    await _assert_assigned(db, therapist, payload.child_id)
    doc = {
        "child_id": payload.child_id, "therapist_id": str(therapist["_id"]),
        "therapist_name": therapist.get("full_name"), "note": payload.note, "tags": payload.tags,
        "created_at": now(),
    }
    result = await db.session_notes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/notes/{child_id}")
async def list_notes(child_id: str, page: int = 1, limit: int = 20, therapist: dict = Depends(require_therapist)):
    """List notes for an assigned child."""
    db = get_database()
    await _assert_assigned(db, therapist, child_id)
    return await paginate(db.session_notes, {"child_id": child_id}, page, limit)


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str, therapist: dict = Depends(require_therapist)):
    """Delete a note authored by this therapist."""
    db = get_database()
    query = {"_id": oid(note_id)}
    if therapist.get("role") != "admin":
        query["therapist_id"] = str(therapist["_id"])
    result = await db.session_notes.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted"}


@router.post("/plans")
async def create_plan(payload: PlanCreate, therapist: dict = Depends(require_therapist)):
    """Create a treatment plan for an assigned child."""
    db = get_database()
    child = await _assert_assigned(db, therapist, payload.child_id)
    assigned_therapist = child.get("therapist_id")
    if not assigned_therapist:
        raise HTTPException(409, detail="Assign a therapist before creating a word plan")
    doc = {
        "child_id": payload.child_id, "therapist_id": assigned_therapist,
        "title": payload.title, "goals": [{"text": g, "done": False} for g in payload.goals],
        "duration_weeks": payload.duration_weeks, "notes": payload.notes, "status": "active",
        "word_ids": payload.word_ids, "vocabulary_version": payload.vocabulary_version,
        "session_limits": payload.session_limits.model_dump(),
        "created_at": now(),
    }
    result = await db.treatment_plans.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/plans/{child_id}")
async def list_plans(child_id: str, therapist: dict = Depends(require_therapist)):
    """List treatment plans for an assigned child."""
    db = get_database()
    await _assert_assigned(db, therapist, child_id)
    rows = await db.treatment_plans.find({"child_id": child_id}).sort("created_at", -1).to_list(length=100)
    return {"plans": serialize(rows)}


@router.patch("/plans/{plan_id}/goal/{goal_index}")
async def toggle_plan_goal(plan_id: str, goal_index: int, therapist: dict = Depends(require_therapist)):
    """Toggle a plan goal's done state."""
    db = get_database()
    plan = await _owned_plan(db, therapist, plan_id)
    goals = plan.get("goals", [])
    if goal_index < 0 or goal_index >= len(goals):
        raise HTTPException(status_code=400, detail="Invalid goal index")
    goals[goal_index]["done"] = not goals[goal_index].get("done", False)
    await db.treatment_plans.update_one({"_id": oid(plan_id)}, {"$set": {"goals": goals}})
    return serialize(await db.treatment_plans.find_one({"_id": oid(plan_id)}))


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, therapist: dict = Depends(require_therapist)):
    """Delete a treatment plan."""
    db = get_database()
    await _owned_plan(db, therapist, plan_id)
    # SES-003: revoke pending claims before retiring the plan; retain history.
    await db.word_sessions.update_many({"plan_id": plan_id, "status": {"$in": ["active", "paused"]}},
        {"$set": {"status": "ended", "inflight_attempt_id": None, "ended_at": now()}})
    await db.treatment_plans.update_one({"_id": oid(plan_id)}, {"$set": {"status": "inactive", "retired_at": now()}})
    return {"message": "Plan retired"}
