"""Privacy router — data export and account deletion requests (GDPR-style).

Backs the Settings > Data & Privacy section. Users can download all their data
and request account deletion, which admins process.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
import json
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/export")
async def export_my_data(current_user: dict = Depends(get_current_user)):
    """Download all data held about the caller as a JSON file."""
    db = get_database()
    uid = str(current_user["_id"])
    bundle = {"profile": serialize(current_user)}
    for coll in ("evaluations", "progress", "notifications", "feedback", "appointments",
                 "quiz_attempts", "game_scores", "wallet_transactions", "goals", "enquiries"):
        rows = await db[coll].find({"user_id": uid}).to_list(length=100000)
        bundle[coll] = serialize(rows)
    content = json.dumps(bundle, indent=2, default=str)
    return Response(content=content, media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename=my_data_{now().strftime('%Y%m%d')}.json"})


@router.post("/delete-request")
async def request_deletion(payload: dict, current_user: dict = Depends(get_current_user)):
    """Request account deletion (queued for admin processing)."""
    db = get_database()
    uid = str(current_user["_id"])
    if await db.deletion_requests.find_one({"user_id": uid, "status": "pending"}):
        raise HTTPException(status_code=409, detail="A deletion request is already pending")
    doc = {"user_id": uid, "email": current_user.get("email"), "reason": payload.get("reason"),
           "status": "pending", "created_at": now()}
    result = await db.deletion_requests.insert_one(doc)
    return {"message": "Deletion request submitted", "id": str(result.inserted_id)}


@router.get("/delete-request")
async def my_deletion_request(current_user: dict = Depends(get_current_user)):
    """Return the caller's pending deletion request, if any."""
    db = get_database()
    doc = await db.deletion_requests.find_one({"user_id": str(current_user["_id"])}, sort=[("created_at", -1)])
    return serialize(doc)


@router.get("/admin/delete-requests")
async def list_deletion_requests(page: int = 1, limit: int = 20, current_admin: dict = Depends(require_admin)):
    """Admin: list account-deletion requests."""
    db = get_database()
    return await paginate(db.deletion_requests, {}, page, limit)


@router.post("/admin/delete-requests/{request_id}/process")
async def process_deletion(request_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: process a deletion request — removes the user and their data."""
    db = get_database()
    req = await db.deletion_requests.find_one({"_id": oid(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    uid = req["user_id"]
    for coll in ("evaluations", "progress", "notifications", "feedback", "appointments",
                 "quiz_attempts", "game_scores", "wallet_transactions", "goals", "enquiries",
                 "wallets", "settings", "reminders", "calendar_events"):
        await db[coll].delete_many({"user_id": uid})
    await db.users.delete_one({"_id": oid(uid)})
    await db.deletion_requests.update_one({"_id": oid(request_id)}, {"$set": {"status": "processed", "processed_at": now()}})
    return {"message": "Account and data deleted"}
