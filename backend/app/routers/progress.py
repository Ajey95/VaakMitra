"""Progress tracking router."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Dict
from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id
from ..services.reward_engine import reward_engine


router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.post("/save")
async def save_progress(
    evaluation_data: Dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Save therapy session progress.
    
    Args:
        evaluation_data: Evaluation result data
        current_user: Authenticated user
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    try:
        # Calculate stars
        stars = reward_engine.calculate_stars(evaluation_data.get("accuracy", 0))
        
        # Create evaluation document
        evaluation_doc = {
            "user_id": user_id,
            "lesson_id": evaluation_data.get("lesson_id"),
            "phoneme": evaluation_data.get("phoneme", ""),
            "lesson_type": evaluation_data.get("lesson_type", "letter"),
            "accuracy": evaluation_data.get("accuracy", 0),
            "phoneme_match": evaluation_data.get("phoneme_match", False),
            "mfcc_score": evaluation_data.get("mfcc_score", 0),
            "gop_score": evaluation_data.get("gop_score", 0),
            "airflow_score": evaluation_data.get("airflow_score", 0),
            "stars_earned": stars,
            "feedback": evaluation_data.get("feedback", ""),
            "syllable_scores": evaluation_data.get("syllable_scores", []),
            "weakest_syllable": evaluation_data.get("weakest_syllable"),
            "duration_ms": evaluation_data.get("duration_ms", 0),
            "created_at": datetime.utcnow()
        }
        
        # Insert evaluation
        await db.evaluations.insert_one(evaluation_doc)
        
        # Update or create progress document
        progress_filter = {
            "user_id": user_id,
            "lesson_id": evaluation_data.get("lesson_id")
        }
        
        existing_progress = await db.progress.find_one(progress_filter)
        
        if existing_progress:
            # Update if this is a better score
            if evaluation_data.get("accuracy", 0) > existing_progress.get("best_accuracy", 0):
                await db.progress.update_one(
                    progress_filter,
                    {
                        "$set": {
                            "best_accuracy": evaluation_data.get("accuracy"),
                            "stars_best": stars,
                            "last_attempted": datetime.utcnow()
                        },
                        "$inc": {"attempts": 1}
                    }
                )
        else:
            # Create new progress document
            progress_doc = {
                "user_id": user_id,
                "lesson_id": evaluation_data.get("lesson_id"),
                "best_accuracy": evaluation_data.get("accuracy", 0),
                "attempts": 1,
                "stars_best": stars,
                "last_attempted": datetime.utcnow(),
                "completed": stars >= 1
            }
            await db.progress.insert_one(progress_doc)
        
        # Update user stats
        await db.users.update_one(
            {"_id": current_user["_id"]},
            {
                "$inc": {
                    "total_sessions": 1,
                    "total_stars": stars
                }
            }
        )
        
        return {
            "message": "Progress saved successfully",
            "stars_earned": stars,
            "accuracy": evaluation_data.get("accuracy", 0)
        }
        
    except Exception as e:
        print(f"Error saving progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to save progress")


@router.get("/user/{user_id}")
async def get_user_progress(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all progress for a user."""
    db = get_database()

    # Resolve "me"/email/_id to the real user id (frontend may not hold _id)
    user_id = resolve_user_id(current_user, user_id)

    # Get all progress documents
    progress_docs = await db.progress.find({"user_id": user_id}).to_list(length=100)
    
    # Get recent evaluations
    evaluations = await db.evaluations.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(10).to_list(length=10)
    
    # Convert ObjectId to string
    for doc in progress_docs:
        doc["_id"] = str(doc["_id"])
    
    for ev in evaluations:
        ev["_id"] = str(ev["_id"])
        ev["created_at"] = ev["created_at"].isoformat()
    
    return {
        "progress": progress_docs,
        "recent_evaluations": evaluations
    }


@router.get("/summary/{user_id}")
async def get_progress_summary(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get aggregated progress summary for a user."""
    db = get_database()

    # Resolve "me"/email/_id to the real user id (frontend may not hold _id)
    user_id = resolve_user_id(current_user, user_id)

    # Get user data
    user = await db.users.find_one({"_id": current_user["_id"]})
    
    # Get progress stats
    progress_docs = await db.progress.find({"user_id": user_id}).to_list(length=100)
    
    # Get recent evaluations for chart data
    evaluations = await db.evaluations.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(10).to_list(length=10)
    
    # Calculate stats
    completed_lessons = len([p for p in progress_docs if p.get("completed")])
    total_lessons = 6
    avg_accuracy = sum([p.get("best_accuracy", 0) for p in progress_docs]) / len(progress_docs) if progress_docs else 0
    
    # Prepare chart data
    chart_data = []
    for ev in reversed(evaluations):
        chart_data.append({
            "date": ev["created_at"].strftime("%m/%d"),
            "accuracy": ev["accuracy"],
            "lesson_id": ev["lesson_id"]
        })
    
    return {
        "total_sessions": user.get("total_sessions", 0),
        "total_stars": user.get("total_stars", 0),
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
        "avg_accuracy": round(avg_accuracy, 2),
        "chart_data": chart_data,
        "progress_by_lesson": progress_docs
    }
