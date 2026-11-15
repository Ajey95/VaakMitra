"""User settings router — server-persisted preferences.

The web app currently keeps settings only in localStorage. This makes them
durable and cross-device (web + Android share the same account settings).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, now

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "dark_mode": False,
    "sound_enabled": True,
    "auto_play": True,
    "text_size": "medium",       # small | medium | large
    "language": "Tamil",
    "currency": "INR",
    "high_contrast": False,
    "reduced_motion": False,
    "notifications": {
        "push": True,
        "email": True,
        "whatsapp": False,
        "reminders": True,
        "achievements": True,
        "offers": False,
        "marketing": False,
        "weekly_report": True,
    },
    "privacy": {
        "share_progress_with_therapist": True,
        "leaderboard_visible": True,
        "profile_public": False,
    },
}


class NotificationSettings(BaseModel):
    push: Optional[bool] = None
    email: Optional[bool] = None
    whatsapp: Optional[bool] = None
    reminders: Optional[bool] = None
    achievements: Optional[bool] = None
    offers: Optional[bool] = None
    marketing: Optional[bool] = None
    weekly_report: Optional[bool] = None


class PrivacySettings(BaseModel):
    share_progress_with_therapist: Optional[bool] = None
    leaderboard_visible: Optional[bool] = None
    profile_public: Optional[bool] = None


class SettingsUpdate(BaseModel):
    dark_mode: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    auto_play: Optional[bool] = None
    text_size: Optional[str] = None
    language: Optional[str] = None
    currency: Optional[str] = None
    high_contrast: Optional[bool] = None
    reduced_motion: Optional[bool] = None
    notifications: Optional[NotificationSettings] = None
    privacy: Optional[PrivacySettings] = None


async def _load(user_id: str) -> dict:
    db = get_database()
    doc = await db.settings.find_one({"user_id": user_id})
    if not doc:
        doc = {"user_id": user_id, **DEFAULT_SETTINGS, "created_at": now(), "updated_at": now()}
        await db.settings.insert_one(doc)
    else:
        # Merge in any new default keys added since the doc was created.
        merged = {**DEFAULT_SETTINGS, **{k: v for k, v in doc.items() if k in DEFAULT_SETTINGS}}
        merged["notifications"] = {**DEFAULT_SETTINGS["notifications"], **doc.get("notifications", {})}
        merged["privacy"] = {**DEFAULT_SETTINGS["privacy"], **doc.get("privacy", {})}
        doc.update(merged)
    return doc


@router.get("")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Return the caller's settings (creating defaults on first access)."""
    doc = await _load(str(current_user["_id"]))
    return serialize(doc)


@router.put("")
async def update_settings(payload: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    """Patch any subset of settings; nested objects merge field-by-field."""
    db = get_database()
    user_id = str(current_user["_id"])
    await _load(user_id)  # ensure exists
    updates = {}
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        if key in ("notifications", "privacy") and isinstance(value, dict):
            for sub, sub_val in value.items():
                updates[f"{key}.{sub}"] = sub_val
        else:
            updates[key] = value
    updates["updated_at"] = now()
    await db.settings.update_one({"user_id": user_id}, {"$set": updates})
    doc = await _load(user_id)
    return serialize(doc)


@router.post("/reset")
async def reset_settings(current_user: dict = Depends(get_current_user)):
    """Reset the caller's settings back to defaults."""
    db = get_database()
    user_id = str(current_user["_id"])
    await db.settings.update_one(
        {"user_id": user_id},
        {"$set": {**DEFAULT_SETTINGS, "updated_at": now()}},
        upsert=True,
    )
    doc = await _load(user_id)
    return serialize(doc)
