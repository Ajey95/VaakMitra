"""Lesson management router — admin CRUD over custom lessons + categories.

The base therapy router serves a fixed 6-lesson catalog. This adds a DB-backed
custom-lesson store so admins/therapists can author new phonemes/words without a
code change, organised into categories.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin, require_therapist
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

LESSON_TYPES = ["letter", "word", "sentence"]


class LessonCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    pronunciation: str
    type: str = "letter"
    category: str = "vowels"
    example_word: Optional[str] = None
    example_sentence: Optional[str] = None
    tips: Optional[str] = None
    difficulty: str = "easy"
    order: int = 0


class LessonUpdate(BaseModel):
    symbol: Optional[str] = None
    pronunciation: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    example_word: Optional[str] = None
    example_sentence: Optional[str] = None
    tips: Optional[str] = None
    difficulty: Optional[str] = None
    order: Optional[int] = None
    active: Optional[bool] = None


class CategoryCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


@router.get("/custom")
async def list_custom_lessons(category: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List active custom lessons (available to all authenticated users)."""
    db = get_database()
    query = {"active": True}
    if category:
        query["category"] = category
    rows = await db.custom_lessons.find(query).sort("order", 1).to_list(length=500)
    return {"lessons": serialize(rows)}


@router.get("/custom/{lesson_id}")
async def get_custom_lesson(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single custom lesson."""
    db = get_database()
    lesson = await db.custom_lessons.find_one({"_id": oid(lesson_id)})
    if not lesson or not lesson.get("active"):
        raise HTTPException(status_code=404, detail="Lesson not found")
    return serialize(lesson)


@router.get("/categories")
async def list_categories(current_user: dict = Depends(get_current_user)):
    """List lesson categories with lesson counts."""
    db = get_database()
    cats = await db.lesson_categories.find({}).to_list(length=100)
    out = serialize(cats)
    for c in out:
        c["lesson_count"] = await db.custom_lessons.count_documents({"category": c.get("slug"), "active": True})
    return {"categories": out}


# ---- Authoring (therapist/admin) ---------------------------------------------

@router.post("/admin")
async def create_lesson(payload: LessonCreate, current_user: dict = Depends(require_therapist)):
    """Therapist/Admin: create a custom lesson."""
    db = get_database()
    doc = {**payload.model_dump(), "active": True, "author": current_user.get("full_name"), "created_at": now()}
    result = await db.custom_lessons.insert_one(doc)
    await audit("lesson.create", current_user, target=str(result.inserted_id))
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.patch("/admin/{lesson_id}")
async def update_lesson(lesson_id: str, payload: LessonUpdate, current_user: dict = Depends(require_therapist)):
    """Therapist/Admin: update a custom lesson."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = now()
    result = await db.custom_lessons.update_one({"_id": oid(lesson_id)}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return serialize(await db.custom_lessons.find_one({"_id": oid(lesson_id)}))


@router.delete("/admin/{lesson_id}")
async def delete_lesson(lesson_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a custom lesson."""
    db = get_database()
    result = await db.custom_lessons.delete_one({"_id": oid(lesson_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lesson not found")
    await audit("lesson.delete", current_admin, target=lesson_id)
    return {"message": "Deleted"}


@router.post("/categories/admin")
async def create_category(payload: CategoryCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a lesson category."""
    db = get_database()
    if await db.lesson_categories.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Category exists")
    doc = {**payload.model_dump(), "created_at": now()}
    result = await db.lesson_categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/categories/admin/{category_id}")
async def delete_category(category_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a lesson category."""
    db = get_database()
    result = await db.lesson_categories.delete_one({"_id": oid(category_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Deleted"}
