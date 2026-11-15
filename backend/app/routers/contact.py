"""Contact form router."""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import List
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
from ..database import get_database
from ..utils.jwt_handler import require_admin


router = APIRouter(prefix="/api/contact", tags=["contact"])


class ContactRequest(BaseModel):
    """Validated contact form submission."""
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=4000)


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_contact(contact_data: ContactRequest):
    """Save a contact form submission (public, validated)."""
    db = get_database()

    contact_doc = {
        "name": contact_data.name.strip(),
        "email": contact_data.email,
        "message": contact_data.message.strip(),
        "created_at": datetime.utcnow(),
        "read": False,
    }

    await db.contacts.insert_one(contact_doc)

    return {"message": "Thank you for contacting us! We'll get back to you soon."}


@router.get("")
async def list_contacts(_admin: dict = Depends(require_admin)):
    """List all contact submissions (admin only)."""
    db = get_database()
    cursor = db.contacts.find().sort("created_at", -1).limit(500)
    contacts = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        contacts.append(doc)
    return {"contacts": contacts, "total": len(contacts)}


@router.patch("/{contact_id}/read")
async def mark_contact_read(contact_id: str, _admin: dict = Depends(require_admin)):
    """Mark a contact submission as read (admin only)."""
    db = get_database()
    if not ObjectId.is_valid(contact_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id")
    result = await db.contacts.update_one(
        {"_id": ObjectId(contact_id)}, {"$set": {"read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"message": "Marked as read"}
