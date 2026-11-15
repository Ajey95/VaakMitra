"""Polls router — quick engagement polls.

Admins publish single-question polls; users vote once and see live results.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/polls", tags=["polls"])


class PollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    options: List[str] = Field(min_length=2, max_length=6)


class VoteRequest(BaseModel):
    option_index: int = Field(ge=0)


@router.get("")
async def list_polls(current_user: dict = Depends(get_current_user)):
    """List active polls with the caller's vote state and live tallies."""
    db = get_database()
    uid = str(current_user["_id"])
    polls = await db.polls.find({"active": True}).sort("created_at", -1).to_list(length=50)
    votes = {v["poll_id"]: v["option_index"] for v in await db.poll_votes.find({"user_id": uid}).to_list(length=500)}
    out = []
    for p in polls:
        item = serialize(p)
        item["my_vote"] = votes.get(str(p["_id"]))
        item["total_votes"] = sum(p.get("tallies", []))
        out.append(item)
    return {"polls": out}


@router.post("/{poll_id}/vote")
async def vote(poll_id: str, payload: VoteRequest, current_user: dict = Depends(get_current_user)):
    """Cast a vote (once per poll)."""
    db = get_database()
    uid = str(current_user["_id"])
    poll = await db.polls.find_one({"_id": oid(poll_id), "active": True})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if payload.option_index >= len(poll["options"]):
        raise HTTPException(status_code=400, detail="Invalid option")
    if await db.poll_votes.find_one({"user_id": uid, "poll_id": poll_id}):
        raise HTTPException(status_code=409, detail="Already voted")
    await db.poll_votes.insert_one({"user_id": uid, "poll_id": poll_id, "option_index": payload.option_index, "created_at": now()})
    tallies = poll.get("tallies", [0] * len(poll["options"]))
    tallies[payload.option_index] += 1
    await db.polls.update_one({"_id": oid(poll_id)}, {"$set": {"tallies": tallies}})
    return {"message": "Vote recorded", "tallies": tallies}


@router.post("/admin")
async def create_poll(payload: PollCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a poll."""
    db = get_database()
    doc = {"question": payload.question, "options": payload.options, "tallies": [0] * len(payload.options),
           "active": True, "created_at": now()}
    result = await db.polls.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/admin/{poll_id}")
async def delete_poll(poll_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a poll and its votes."""
    db = get_database()
    result = await db.polls.delete_one({"_id": oid(poll_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Poll not found")
    await db.poll_votes.delete_many({"poll_id": poll_id})
    return {"message": "Deleted"}
