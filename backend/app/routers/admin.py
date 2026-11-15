"""Admin router for user management and analytics."""
from fastapi import APIRouter, Depends, HTTPException, Response
from datetime import datetime, timedelta
from typing import List, Optional
import csv
import io
from ..database import get_database
from ..utils.jwt_handler import require_admin


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def get_users(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    current_admin: dict = Depends(require_admin)
):
    """Get paginated list of users."""
    db = get_database()
    
    # Build query
    query = {"role": "user"}
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"child_name": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.users.count_documents(query)
    
    # Get paginated results
    skip = (page - 1) * limit
    users = await db.users.find(query).skip(skip).limit(limit).sort("created_at", -1).to_list(length=limit)
    
    # Convert ObjectId to string and remove password
    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        user["created_at"] = user["created_at"].isoformat()
        if user.get("last_login"):
            user["last_login"] = user["last_login"].isoformat()
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    current_admin: dict = Depends(require_admin)
):
    """Get detailed user information."""
    db = get_database()
    
    # Get user from database by email (since user_id might be email)
    from bson import ObjectId
    
    # Try as ObjectId first, then as email
    try:
        if ObjectId.is_valid(user_id):
            user = await db.users.find_one({"_id": ObjectId(user_id)})
        else:
            user = await db.users.find_one({"email": user_id})
    except:
        user = await db.users.find_one({"email": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id_str = str(user["_id"])
    
    # Get evaluations
    evaluations = await db.evaluations.find(
        {"user_id": user_id_str}
    ).sort("created_at", -1).limit(50).to_list(length=50)
    
    # Get progress
    progress = await db.progress.find({"user_id": user_id_str}).to_list(length=100)
    
    # Convert ObjectId to string
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    
    for ev in evaluations:
        ev["_id"] = str(ev["_id"])
        ev["created_at"] = ev["created_at"].isoformat()
    
    for prog in progress:
        prog["_id"] = str(prog["_id"])
        if prog.get("last_attempted"):
            prog["last_attempted"] = prog["last_attempted"].isoformat()
    
    return {
        "user": user,
        "evaluations": evaluations,
        "progress": progress
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: dict = Depends(require_admin)
):
    """Delete a user and all their data."""
    db = get_database()
    
    from bson import ObjectId
    
    # Try as ObjectId first
    try:
        if ObjectId.is_valid(user_id):
            query = {"_id": ObjectId(user_id)}
        else:
            query = {"email": user_id}
    except:
        query = {"email": user_id}
    
    # Delete user
    result = await db.users.delete_one(query)
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user's evaluations and progress
    await db.evaluations.delete_many({"user_id": user_id})
    await db.progress.delete_many({"user_id": user_id})
    
    return {"message": "User deleted successfully"}


@router.get("/stats")
async def get_stats(current_admin: dict = Depends(require_admin)):
    """Get overall platform statistics."""
    db = get_database()
    
    # Count users
    total_users = await db.users.count_documents({"role": "user"})
    
    # Count today's sessions
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sessions_today = await db.evaluations.count_documents({
        "created_at": {"$gte": today_start}
    })
    
    # Get all evaluations for average accuracy
    all_evaluations = await db.evaluations.find().to_list(length=10000)
    avg_accuracy = sum([ev.get("accuracy", 0) for ev in all_evaluations]) / len(all_evaluations) if all_evaluations else 0
    
    # Total stars given
    all_users = await db.users.find({"role": "user"}).to_list(length=10000)
    total_stars = sum([u.get("total_stars", 0) for u in all_users])
    
    # Sessions per day (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_evaluations = await db.evaluations.find({
        "created_at": {"$gte": thirty_days_ago}
    }).to_list(length=10000)
    
    # Group by date
    sessions_by_date = {}
    for ev in recent_evaluations:
        date_key = ev["created_at"].strftime("%Y-%m-%d")
        sessions_by_date[date_key] = sessions_by_date.get(date_key, 0) + 1
    
    # Accuracy per lesson
    accuracy_by_lesson = {}
    for ev in all_evaluations:
        lesson_id = ev.get("lesson_id", 0)
        if lesson_id not in accuracy_by_lesson:
            accuracy_by_lesson[lesson_id] = []
        accuracy_by_lesson[lesson_id].append(ev.get("accuracy", 0))
    
    lesson_averages = {
        lesson_id: sum(accuracies) / len(accuracies)
        for lesson_id, accuracies in accuracy_by_lesson.items()
    }
    
    return {
        "total_users": total_users,
        "sessions_today": sessions_today,
        "avg_accuracy": round(avg_accuracy, 2),
        "total_stars": total_stars,
        "sessions_by_date": sessions_by_date,
        "accuracy_by_lesson": lesson_averages,
        "total_sessions": len(all_evaluations)
    }


@router.get("/export/csv")
async def export_csv(current_admin: dict = Depends(require_admin)):
    """Export all user data as CSV."""
    db = get_database()
    
    # Get all users
    users = await db.users.find({"role": "user"}).to_list(length=10000)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Email", "Full Name", "Child Name", "Child Age",
        "Total Sessions", "Total Stars", "Created At", "Last Login"
    ])
    
    # Data rows
    for user in users:
        writer.writerow([
            user.get("email", ""),
            user.get("full_name", ""),
            user.get("child_name", ""),
            user.get("child_age", ""),
            user.get("total_sessions", 0),
            user.get("total_stars", 0),
            user.get("created_at", ""),
            user.get("last_login", "")
        ])
    
    # Return CSV
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=users_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }
    )


# Contact submissions are handled by the dedicated contact router
# (app/routers/contact.py), which includes validation and admin read access.
