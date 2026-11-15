"""Glossary router — Tamil phoneme/word dictionary reference.

A searchable reference of sounds and words with pronunciation guidance. Admins
curate entries; all users search/read.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/glossary", tags=["glossary"])

DEFAULT_ENTRIES = [
    {"term": "அ", "roman": "a", "type": "vowel", "meaning": "Short 'a' vowel.", "example": "அம்மா (amma)"},
    {"term": "ஆ", "roman": "aa", "type": "vowel", "meaning": "Long 'aa' vowel.", "example": "ஆடு (aadu)"},
    {"term": "ல", "roman": "la", "type": "consonant", "meaning": "'la' consonant.", "example": "லட்டு (laddu)"},
    {"term": "த", "roman": "ta", "type": "consonant", "meaning": "'ta' consonant.", "example": "தமிழ் (tamizh)"},
]


class EntryCreate(BaseModel):
    term: str
    roman: str
    type: str = "vowel"
    meaning: str = ""
    example: Optional[str] = None


@router.get("")
async def list_entries(page: int = 1, limit: int = 30, type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List glossary entries (seeds defaults on first call)."""
    db = get_database()
    if await db.glossary.count_documents({}) == 0:
        await db.glossary.insert_many([{**e, "created_at": now()} for e in DEFAULT_ENTRIES])
    query = {"type": type} if type else {}
    return await paginate(db.glossary, query, page, limit, sort_field="roman", sort_dir=1)


@router.get("/search")
async def search_entries(q: str = Query(min_length=1), current_user: dict = Depends(get_current_user)):
    """Search glossary by term/roman/meaning."""
    db = get_database()
    rx = {"$regex": q, "$options": "i"}
    rows = await db.glossary.find({"$or": [{"term": rx}, {"roman": rx}, {"meaning": rx}]}).limit(30).to_list(length=30)
    return {"results": serialize(rows)}


@router.get("/{entry_id}")
async def get_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single glossary entry."""
    db = get_database()
    entry = await db.glossary.find_one({"_id": oid(entry_id)})
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return serialize(entry)


@router.post("/admin")
async def create_entry(payload: EntryCreate, current_admin: dict = Depends(require_admin)):
    """Admin: add a glossary entry."""
    db = get_database()
    doc = {**payload.model_dump(), "created_at": now()}
    result = await db.glossary.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/admin/{entry_id}")
async def delete_entry(entry_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a glossary entry."""
    db = get_database()
    result = await db.glossary.delete_one({"_id": oid(entry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Deleted"}
