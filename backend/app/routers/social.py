"""Social router — friends, activity and expanded leaderboards.

Adds a light social layer: send/accept friend requests, view a friends
leaderboard, and see friends' recent milestones. Respects the privacy setting
`leaderboard_visible`.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now
from .notifications import push_notification

router = APIRouter(prefix="/api/social", tags=["social"])


class FriendRequest(BaseModel):
    email: str


@router.post("/friends/request")
async def send_request(payload: FriendRequest, current_user: dict = Depends(get_current_user)):
    """Send a friend request by email."""
    db = get_database()
    target = await db.users.find_one({"email": payload.email.lower().strip()})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target["_id"]) == str(current_user["_id"]):
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    existing = await db.friendships.find_one({
        "$or": [
            {"a": str(current_user["_id"]), "b": str(target["_id"])},
            {"a": str(target["_id"]), "b": str(current_user["_id"])},
        ]
    })
    if existing:
        raise HTTPException(status_code=409, detail=f"Already {existing['status']}")
    doc = {
        "a": str(current_user["_id"]), "b": str(target["_id"]),
        "requester": str(current_user["_id"]), "status": "pending", "created_at": now(),
    }
    result = await db.friendships.insert_one(doc)
    await push_notification(str(target["_id"]), "New friend request",
                            f"{current_user.get('full_name')} wants to be friends.",
                            category="social", link="/friends")
    return {"message": "Request sent", "id": str(result.inserted_id)}


@router.get("/friends")
async def list_friends(current_user: dict = Depends(get_current_user)):
    """List accepted friends."""
    db = get_database()
    uid = str(current_user["_id"])
    rows = await db.friendships.find({"status": "accepted", "$or": [{"a": uid}, {"b": uid}]}).to_list(length=1000)
    friend_ids = [r["b"] if r["a"] == uid else r["a"] for r in rows]
    friends = await db.users.find({"_id": {"$in": [oid(i) for i in friend_ids]}},
                                  {"full_name": 1, "child_name": 1, "total_stars": 1, "avatar_url": 1}).to_list(length=1000)
    return {"friends": serialize(friends)}


@router.get("/friends/requests")
async def pending_requests(current_user: dict = Depends(get_current_user)):
    """List incoming pending friend requests."""
    db = get_database()
    uid = str(current_user["_id"])
    rows = await db.friendships.find({"status": "pending", "b": uid, "requester": {"$ne": uid}}).to_list(length=500)
    # Also catch cases where requester is 'a' and current is 'b'
    reqs = []
    for r in rows:
        requester = await db.users.find_one({"_id": oid(r["requester"])}, {"full_name": 1, "child_name": 1})
        reqs.append({"id": str(r["_id"]), "requester": serialize(requester)})
    return {"requests": reqs}


@router.post("/friends/{friendship_id}/accept")
async def accept_request(friendship_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a pending friend request addressed to the caller."""
    db = get_database()
    uid = str(current_user["_id"])
    fr = await db.friendships.find_one({"_id": oid(friendship_id)})
    if not fr or uid not in (fr["a"], fr["b"]) or fr["requester"] == uid:
        raise HTTPException(status_code=404, detail="Request not found")
    await db.friendships.update_one({"_id": oid(friendship_id)}, {"$set": {"status": "accepted", "accepted_at": now()}})
    await push_notification(fr["requester"], "Friend request accepted",
                            f"{current_user.get('full_name')} accepted your request.", category="social")
    return {"message": "Friend added"}


@router.delete("/friends/{friendship_id}")
async def remove_friend(friendship_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a friend or decline a request."""
    db = get_database()
    uid = str(current_user["_id"])
    result = await db.friendships.delete_one({"_id": oid(friendship_id), "$or": [{"a": uid}, {"b": uid}]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Removed"}


@router.get("/leaderboard/friends")
async def friends_leaderboard(current_user: dict = Depends(get_current_user)):
    """Leaderboard limited to the caller and their friends, ranked by stars."""
    db = get_database()
    uid = str(current_user["_id"])
    rows = await db.friendships.find({"status": "accepted", "$or": [{"a": uid}, {"b": uid}]}).to_list(length=1000)
    ids = [uid] + [r["b"] if r["a"] == uid else r["a"] for r in rows]
    users = await db.users.find({"_id": {"$in": [oid(i) for i in ids]}}).sort("total_stars", -1).to_list(length=1000)
    board = [{"rank": i + 1, "name": u.get("child_name") or u.get("full_name"),
              "stars": u.get("total_stars", 0), "is_me": str(u["_id"]) == uid}
             for i, u in enumerate(users)]
    return {"leaderboard": board}


@router.get("/leaderboard/global")
async def global_leaderboard(limit: int = Query(default=20, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    """Global leaderboard by stars (respects leaderboard_visible privacy)."""
    db = get_database()
    users = await db.users.find({"role": "user"}).sort("total_stars", -1).limit(limit * 2).to_list(length=limit * 2)
    board, rank = [], 0
    for u in users:
        s = await db.settings.find_one({"user_id": str(u["_id"])})
        if s and s.get("privacy", {}).get("leaderboard_visible") is False:
            continue
        rank += 1
        board.append({"rank": rank, "name": u.get("child_name") or "Learner",
                      "stars": u.get("total_stars", 0), "is_me": str(u["_id"]) == str(current_user["_id"])})
        if rank >= limit:
            break
    return {"leaderboard": board}
