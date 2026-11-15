"""Reviews router — star ratings & reviews for lessons/videos/games.

Users rate content 1-5 with an optional comment; aggregate ratings feed content
cards and admin quality dashboards.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

TARGETS = ["lesson", "video", "game", "quiz"]


class ReviewCreate(BaseModel):
    target_type: str
    target_ref: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


@router.post("")
async def add_review(payload: ReviewCreate, current_user: dict = Depends(get_current_user)):
    """Add or update the caller's review for a content item."""
    if payload.target_type not in TARGETS:
        raise HTTPException(status_code=400, detail="Invalid target type")
    db = get_database()
    uid = str(current_user["_id"])
    await db.reviews.update_one(
        {"user_id": uid, "target_type": payload.target_type, "target_ref": payload.target_ref},
        {"$set": {"rating": payload.rating, "comment": payload.comment,
                  "user_name": current_user.get("full_name"), "updated_at": now()},
         "$setOnInsert": {"created_at": now()}},
        upsert=True,
    )
    return {"message": "Review saved"}


@router.get("/{target_type}/{target_ref}")
async def list_reviews(target_type: str, target_ref: str, page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """List reviews for a content item plus its average rating."""
    db = get_database()
    query = {"target_type": target_type, "target_ref": target_ref}
    result = await paginate(db.reviews, query, page, limit)
    all_rows = await db.reviews.find(query, {"rating": 1}).to_list(length=100000)
    ratings = [r["rating"] for r in all_rows]
    result["average_rating"] = round(sum(ratings) / len(ratings), 2) if ratings else 0
    result["rating_count"] = len(ratings)
    return result


@router.get("/mine/all")
async def my_reviews(current_user: dict = Depends(get_current_user)):
    """List reviews written by the caller."""
    db = get_database()
    rows = await db.reviews.find({"user_id": str(current_user["_id"])}).sort("updated_at", -1).to_list(length=500)
    return {"reviews": serialize(rows)}


@router.delete("/{review_id}")
async def delete_review(review_id: str, current_user: dict = Depends(get_current_user)):
    """Delete the caller's review."""
    db = get_database()
    result = await db.reviews.delete_one({"_id": oid(review_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Deleted"}
