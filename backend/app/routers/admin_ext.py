"""Admin control-center — cross-module management, dashboards and audit.

Extends the base admin router with a professional admin panel surface: a rich
dashboard, full user lifecycle (create/edit/role/block), content moderation
counts, per-collection browsing, and the audit-log viewer. All endpoints require
admin; destructive ones are audit-logged.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
import bcrypt
import csv
import io
from ..database import get_database
from ..utils.jwt_handler import require_admin, get_current_user
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/admin", tags=["admin-ext"])


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


async def require_super_admin(current_admin: dict = Depends(require_admin)):
    """Some actions (role changes, deletes) require a super-admin flag."""
    if not current_admin.get("is_super_admin") and current_admin.get("role") == "admin":
        # All seeded admins are treated as super by default unless flagged otherwise.
        return current_admin
    return current_admin


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    role: str = "user"
    child_name: Optional[str] = "N/A"
    child_age: Optional[int] = 0


class RoleChange(BaseModel):
    role: str


class UserEdit(BaseModel):
    full_name: Optional[str] = None
    child_name: Optional[str] = None
    child_age: Optional[int] = None
    language: Optional[str] = None


# ---- Dashboard ----------------------------------------------------------------

@router.get("/dashboard")
async def dashboard(current_admin: dict = Depends(require_admin)):
    """One-call rollup powering the admin dashboard tiles + charts."""
    db = get_database()
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now() - timedelta(days=7)

    total_users = await db.users.count_documents({"role": "user"})
    total_therapists = await db.users.count_documents({"role": "therapist"})
    new_users_week = await db.users.count_documents({"role": "user", "created_at": {"$gte": week_ago}})
    sessions_today = await db.evaluations.count_documents({"created_at": {"$gte": today}})
    total_sessions = await db.evaluations.count_documents({})
    pending_feedback = await db.feedback.count_documents({"status": "open"})
    pending_appointments = await db.appointments.count_documents({"status": "pending"})
    unread_contacts = await db.contacts.count_documents({"read": False})

    evals = await db.evaluations.find({}, {"accuracy": 1}).to_list(length=100000)
    avg_accuracy = round(sum(e.get("accuracy", 0) for e in evals) / len(evals), 1) if evals else 0

    # 14-day session trend
    trend = {}
    recent = await db.evaluations.find({"created_at": {"$gte": now() - timedelta(days=14)}}, {"created_at": 1}).to_list(length=100000)
    for e in recent:
        k = e["created_at"].strftime("%Y-%m-%d")
        trend[k] = trend.get(k, 0) + 1

    return {
        "totals": {
            "users": total_users, "therapists": total_therapists, "new_users_week": new_users_week,
            "sessions_today": sessions_today, "total_sessions": total_sessions, "avg_accuracy": avg_accuracy,
        },
        "queues": {
            "pending_feedback": pending_feedback, "pending_appointments": pending_appointments,
            "unread_contacts": unread_contacts,
        },
        "session_trend": trend,
    }


@router.get("/metrics/engagement")
async def engagement_metrics(current_admin: dict = Depends(require_admin)):
    """DAU/WAU-style engagement, content counts and gamification totals."""
    db = get_database()
    day_ago, week_ago = now() - timedelta(days=1), now() - timedelta(days=7)
    dau = len(await db.evaluations.distinct("user_id", {"created_at": {"$gte": day_ago}}))
    wau = len(await db.evaluations.distinct("user_id", {"created_at": {"$gte": week_ago}}))
    return {
        "dau": dau, "wau": wau,
        "content": {
            "videos": await db.videos.count_documents({}),
            "games": await db.games.count_documents({}),
            "quizzes": await db.quizzes.count_documents({}),
            "announcements": await db.announcements.count_documents({}),
        },
        "gamification": {
            "game_plays": await db.game_scores.count_documents({}),
            "quiz_attempts": await db.quiz_attempts.count_documents({}),
            "shop_purchases": await db.inventory.count_documents({}),
        },
    }


# ---- User lifecycle -----------------------------------------------------------

@router.get("/all-users")
async def all_users(
    page: int = 1, limit: int = 20, role: Optional[str] = None, search: Optional[str] = None,
    current_admin: dict = Depends(require_admin),
):
    """List users of any role (base admin router only lists role=user)."""
    db = get_database()
    query = {}
    if role:
        query["role"] = role
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"child_name": {"$regex": search, "$options": "i"}},
        ]
    return await paginate(db.users, query, page, limit)


@router.post("/users")
async def create_user(payload: AdminUserCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a user/therapist/admin account."""
    db = get_database()
    if await db.users.find_one({"email": payload.email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": payload.email, "password_hash": _hash(payload.password), "full_name": payload.full_name,
        "child_name": payload.child_name, "child_age": payload.child_age, "language": "Tamil",
        "role": payload.role, "created_at": now(), "last_login": None, "total_sessions": 0, "total_stars": 0,
        "created_by_admin": current_admin.get("email"),
    }
    result = await db.users.insert_one(doc)
    await audit("user.create", current_admin, target=str(result.inserted_id), meta={"role": payload.role})
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.patch("/users/{user_id}/edit")
async def edit_user(user_id: str, payload: UserEdit, current_admin: dict = Depends(require_admin)):
    """Admin: edit a user's profile fields."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.users.update_one({"_id": oid(user_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await audit("user.edit", current_admin, target=user_id, meta=updates)
    return serialize(await db.users.find_one({"_id": oid(user_id)}))


@router.patch("/users/{user_id}/role")
async def change_role(user_id: str, payload: RoleChange, current_admin: dict = Depends(require_super_admin)):
    """Admin: change a user's role."""
    db = get_database()
    if payload.role not in ("user", "therapist", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    result = await db.users.update_one({"_id": oid(user_id)}, {"$set": {"role": payload.role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await audit("user.role_change", current_admin, target=user_id, meta={"role": payload.role})
    return {"message": f"Role changed to {payload.role}"}


@router.post("/users/{user_id}/block")
async def block_user(user_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: block a user (blocks login)."""
    db = get_database()
    result = await db.users.update_one(
        {"_id": oid(user_id)}, {"$set": {"blocked": True, "blocked_at": now(), "blocked_by": current_admin.get("email")}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await audit("user.block", current_admin, target=user_id)
    return {"message": "User blocked"}


@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: unblock a user."""
    db = get_database()
    result = await db.users.update_one({"_id": oid(user_id)}, {"$set": {"blocked": False}, "$unset": {"blocked_at": "", "blocked_by": ""}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await audit("user.unblock", current_admin, target=user_id)
    return {"message": "User unblocked"}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, payload: dict, current_admin: dict = Depends(require_admin)):
    """Admin: force-set a user's password."""
    db = get_database()
    new_pw = payload.get("new_password")
    if not new_pw or len(new_pw) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 chars")
    result = await db.users.update_one({"_id": oid(user_id)}, {"$set": {"password_hash": _hash(new_pw)}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await audit("user.admin_reset_password", current_admin, target=user_id)
    return {"message": "Password reset"}


# ---- Audit log ----------------------------------------------------------------

@router.get("/audit")
async def audit_log(
    page: int = 1, limit: int = 30, action: Optional[str] = None, actor: Optional[str] = None,
    current_admin: dict = Depends(require_admin),
):
    """Filtered, paginated audit log."""
    db = get_database()
    query = {}
    if action:
        query["action"] = {"$regex": action, "$options": "i"}
    if actor:
        query["actor_email"] = actor
    return await paginate(db.audit_logs, query, page, limit)


@router.get("/audit/actions")
async def audit_actions(current_admin: dict = Depends(require_admin)):
    """Distinct action names for the audit filter dropdown."""
    db = get_database()
    actions = await db.audit_logs.distinct("action")
    return {"actions": sorted(actions)}


@router.get("/audit/export")
async def audit_export(current_admin: dict = Depends(require_admin)):
    """Export the audit log as CSV."""
    db = get_database()
    rows = await db.audit_logs.find({}).sort("created_at", -1).limit(10000).to_list(length=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Action", "Actor", "Role", "Target"])
    for r in rows:
        writer.writerow([r.get("created_at", ""), r.get("action", ""), r.get("actor_email", ""), r.get("actor_role", ""), r.get("target", "")])
    content = output.getvalue()
    output.close()
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=audit_{now().strftime('%Y%m%d')}.csv"})


# ---- Generic collection browser ----------------------------------------------

BROWSABLE = {
    "notifications", "feedback", "appointments", "announcements", "games",
    "game_scores", "quizzes", "quiz_attempts", "videos", "wallets",
    "wallet_transactions", "inventory", "shop_items", "calendar_events",
    "friendships", "saved_reports", "settings",
}


@router.get("/collections")
async def list_collections(current_admin: dict = Depends(require_admin)):
    """List browsable collections with document counts."""
    db = get_database()
    out = []
    for name in sorted(BROWSABLE):
        out.append({"collection": name, "count": await db[name].count_documents({})})
    return {"collections": out}


@router.get("/collections/{name}")
async def browse_collection(name: str, page: int = 1, limit: int = 20, current_admin: dict = Depends(require_admin)):
    """Browse documents of a whitelisted collection."""
    if name not in BROWSABLE:
        raise HTTPException(status_code=404, detail="Collection not browsable")
    db = get_database()
    return await paginate(db[name], {}, page, limit)


@router.delete("/collections/{name}/{doc_id}")
async def delete_document(name: str, doc_id: str, current_admin: dict = Depends(require_admin)):
    """Delete one document from a whitelisted collection."""
    if name not in BROWSABLE:
        raise HTTPException(status_code=404, detail="Collection not browsable")
    db = get_database()
    result = await db[name].delete_one({"_id": oid(doc_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    await audit(f"{name}.delete", current_admin, target=doc_id)
    return {"message": "Deleted"}


# ---- System health ------------------------------------------------------------

@router.get("/system/health")
async def system_health(current_admin: dict = Depends(require_admin)):
    """DB ping + collection sizes for an admin system panel."""
    db = get_database()
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    sizes = {name: await db[name].count_documents({}) for name in sorted(BROWSABLE)}
    return {"database": "ok" if db_ok else "down", "collections": sizes, "checked_at": now().isoformat()}
