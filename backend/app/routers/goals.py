"""Goals & challenges router.

Users (or their parent/therapist) set practice goals (e.g. "10 sessions this
week", "reach 80% on அ"). Challenges are system-defined time-boxed goals with a
coin reward on completion.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/goals", tags=["goals"])

GOAL_TYPES = ["sessions", "accuracy", "streak", "stars", "lessons"]


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    type: str = "sessions"
    target: float = Field(gt=0)
    deadline: Optional[str] = None


class ChallengeCreate(BaseModel):
    title: str
    description: str = ""
    type: str = "sessions"
    target: float
    coin_reward: int = 50
    days: int = 7


async def _progress_value(user_id: str, goal_type: str) -> float:
    """Compute current progress for a goal from live data."""
    db = get_database()
    if goal_type == "sessions":
        return await db.evaluations.count_documents({"user_id": user_id})
    if goal_type == "stars":
        u = await db.users.find_one({"_id": oid(user_id)})
        return u.get("total_stars", 0) if u else 0
    if goal_type == "accuracy":
        evals = await db.evaluations.find({"user_id": user_id}, {"accuracy": 1}).sort("created_at", -1).limit(10).to_list(length=10)
        return round(sum(e.get("accuracy", 0) for e in evals) / len(evals), 1) if evals else 0
    if goal_type == "lessons":
        return await db.progress.count_documents({"user_id": user_id, "completed": True})
    if goal_type == "streak":
        w = await db.wallets.find_one({"user_id": user_id})
        return w.get("daily_streak", 0) if w else 0
    return 0


@router.post("")
async def create_goal(payload: GoalCreate, current_user: dict = Depends(get_current_user)):
    """Create a personal goal."""
    db = get_database()
    if payload.type not in GOAL_TYPES:
        raise HTTPException(status_code=400, detail="Invalid goal type")
    doc = {
        "user_id": str(current_user["_id"]), "title": payload.title, "type": payload.type,
        "target": payload.target, "start_value": await _progress_value(str(current_user["_id"]), payload.type),
        "deadline": payload.deadline, "completed": False, "created_at": now(),
    }
    result = await db.goals.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def list_goals(current_user: dict = Depends(get_current_user)):
    """List goals with live progress %."""
    db = get_database()
    uid = str(current_user["_id"])
    goals = await db.goals.find({"user_id": uid}).sort("created_at", -1).to_list(length=200)
    out = []
    for g in goals:
        current = await _progress_value(uid, g["type"])
        gained = max(0, current - g.get("start_value", 0)) if g["type"] in ("sessions", "stars", "lessons") else current
        pct = min(100, round(gained / g["target"] * 100, 1)) if g["target"] else 0
        item = serialize(g)
        item["current"] = current
        item["progress_pct"] = pct
        if pct >= 100 and not g.get("completed"):
            await db.goals.update_one({"_id": g["_id"]}, {"$set": {"completed": True, "completed_at": now()}})
            item["completed"] = True
        out.append(item)
    return {"goals": out}


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a goal."""
    db = get_database()
    result = await db.goals.delete_one({"_id": oid(goal_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted"}


# ---- Challenges (system) ------------------------------------------------------

@router.get("/challenges")
async def list_challenges(current_user: dict = Depends(get_current_user)):
    """List active challenges with the caller's join/complete state."""
    db = get_database()
    uid = str(current_user["_id"])
    challenges = await db.challenges.find({"active": True}).to_list(length=100)
    joined = {j["challenge_id"]: j for j in await db.challenge_joins.find({"user_id": uid}).to_list(length=500)}
    out = []
    for c in challenges:
        item = serialize(c)
        j = joined.get(str(c["_id"]))
        item["joined"] = bool(j)
        item["completed"] = bool(j and j.get("completed"))
        out.append(item)
    return {"challenges": out}


@router.post("/challenges/{challenge_id}/join")
async def join_challenge(challenge_id: str, current_user: dict = Depends(get_current_user)):
    """Join a challenge."""
    db = get_database()
    uid = str(current_user["_id"])
    challenge = await db.challenges.find_one({"_id": oid(challenge_id), "active": True})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if await db.challenge_joins.find_one({"user_id": uid, "challenge_id": challenge_id}):
        raise HTTPException(status_code=409, detail="Already joined")
    await db.challenge_joins.insert_one({
        "user_id": uid, "challenge_id": challenge_id, "type": challenge["type"],
        "start_value": await _progress_value(uid, challenge["type"]),
        "completed": False, "joined_at": now(),
    })
    return {"message": "Joined challenge"}


@router.post("/challenges/{challenge_id}/claim")
async def claim_challenge(challenge_id: str, current_user: dict = Depends(get_current_user)):
    """Claim a completed challenge's reward."""
    db = get_database()
    uid = str(current_user["_id"])
    join = await db.challenge_joins.find_one({"user_id": uid, "challenge_id": challenge_id})
    challenge = await db.challenges.find_one({"_id": oid(challenge_id)})
    if not join or not challenge:
        raise HTTPException(status_code=404, detail="Not joined")
    if join.get("completed"):
        raise HTTPException(status_code=409, detail="Already claimed")
    current = await _progress_value(uid, challenge["type"])
    gained = max(0, current - join.get("start_value", 0))
    if gained < challenge["target"]:
        raise HTTPException(status_code=400, detail=f"Not complete yet ({gained}/{challenge['target']})")
    await db.challenge_joins.update_one({"_id": join["_id"]}, {"$set": {"completed": True, "completed_at": now()}})
    from .wallet import credit_wallet
    await credit_wallet(uid, coins=challenge.get("coin_reward", 50), reason=f"Challenge: {challenge['title']}")
    return {"message": "Reward claimed", "coins": challenge.get("coin_reward", 50)}


@router.post("/challenges/admin")
async def create_challenge(payload: ChallengeCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a challenge."""
    db = get_database()
    doc = {**payload.model_dump(), "active": True, "ends_at": now() + timedelta(days=payload.days), "created_at": now()}
    result = await db.challenges.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)
