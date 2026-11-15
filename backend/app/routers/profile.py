"""Profile router — extended user & child profile.

Backs the multi-tab Profile page (Personal, Child, Medical, Emergency,
Preferences). The core auth user doc holds identity; richer structured data
lives on the same document under namespaced sub-objects.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/profile", tags=["profile"])


class PersonalUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    city: Optional[str] = None
    avatar_url: Optional[str] = None
    dob: Optional[str] = None


class ChildUpdate(BaseModel):
    child_name: Optional[str] = Field(default=None, max_length=120)
    child_age: Optional[int] = Field(default=None, ge=2, le=18)
    child_gender: Optional[str] = None
    language: Optional[str] = None
    diagnosis_age: Optional[int] = None


class MedicalUpdate(BaseModel):
    diagnosis: Optional[str] = None
    severity: Optional[str] = None          # mild | moderate | severe
    allergies: Optional[str] = None
    medications: Optional[str] = None
    therapist_name: Optional[str] = None
    notes: Optional[str] = None


class EmergencyContact(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    relationship: str = Field(min_length=1, max_length=60)
    phone: str = Field(min_length=3, max_length=20)
    email: Optional[EmailStr] = None


class PreferencesUpdate(BaseModel):
    diet: Optional[str] = None
    favorite_reward: Optional[str] = None
    learning_pace: Optional[str] = None     # slow | normal | fast
    preferred_time: Optional[str] = None
    interests: Optional[List[str]] = None


@router.get("")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Return the full profile (all tabs) for the current user."""
    doc = serialize(current_user)
    doc.setdefault("medical", {})
    doc.setdefault("preferences", {})
    doc.setdefault("emergency_contacts", [])
    return doc


@router.patch("/personal")
async def update_personal(payload: PersonalUpdate, current_user: dict = Depends(get_current_user)):
    """Update personal identity fields."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    updates["updated_at"] = now()
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    doc = await db.users.find_one({"_id": current_user["_id"]})
    return serialize(doc)


@router.patch("/child")
async def update_child(payload: ChildUpdate, current_user: dict = Depends(get_current_user)):
    """Update the child profile fields."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    updates["updated_at"] = now()
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    doc = await db.users.find_one({"_id": current_user["_id"]})
    return serialize(doc)


@router.patch("/medical")
async def update_medical(payload: MedicalUpdate, current_user: dict = Depends(get_current_user)):
    """Update medical details (stored under the 'medical' sub-object)."""
    db = get_database()
    updates = {f"medical.{k}": v for k, v in payload.model_dump(exclude_none=True).items()}
    updates["updated_at"] = now()
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    doc = await db.users.find_one({"_id": current_user["_id"]})
    return serialize(doc)


@router.patch("/preferences")
async def update_preferences(payload: PreferencesUpdate, current_user: dict = Depends(get_current_user)):
    """Update learning/reward preferences."""
    db = get_database()
    updates = {f"preferences.{k}": v for k, v in payload.model_dump(exclude_none=True).items()}
    updates["updated_at"] = now()
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    doc = await db.users.find_one({"_id": current_user["_id"]})
    return serialize(doc)


# ---- Emergency contacts (list on the user doc) --------------------------------

@router.get("/emergency-contacts")
async def list_emergency(current_user: dict = Depends(get_current_user)):
    """List emergency contacts."""
    db = get_database()
    doc = await db.users.find_one({"_id": current_user["_id"]}, {"emergency_contacts": 1})
    return serialize(doc.get("emergency_contacts", []) if doc else [])


@router.post("/emergency-contacts")
async def add_emergency(payload: EmergencyContact, current_user: dict = Depends(get_current_user)):
    """Add an emergency contact."""
    db = get_database()
    from bson import ObjectId
    contact = payload.model_dump()
    contact["_id"] = str(ObjectId())
    contact["created_at"] = now().isoformat()
    await db.users.update_one({"_id": current_user["_id"]}, {"$push": {"emergency_contacts": contact}})
    return {"message": "Contact added", "contact": contact}


@router.delete("/emergency-contacts/{contact_id}")
async def delete_emergency(contact_id: str, current_user: dict = Depends(get_current_user)):
    """Remove an emergency contact by its generated id."""
    db = get_database()
    result = await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$pull": {"emergency_contacts": {"_id": contact_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"message": "Contact removed"}


@router.post("/avatar")
async def set_avatar(payload: dict, current_user: dict = Depends(get_current_user)):
    """Set avatar URL (image upload handled client-side / by storage provider)."""
    db = get_database()
    url = payload.get("avatar_url")
    if not url:
        raise HTTPException(status_code=400, detail="avatar_url required")
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": {"avatar_url": url}})
    return {"message": "Avatar updated", "avatar_url": url}
