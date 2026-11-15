"""Devices router — register push-notification tokens.

Mobile (and web) clients register a device token so the platform can target
push notifications. Tokens are deduped per user+token.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceRegister(BaseModel):
    token: str = Field(min_length=1)
    platform: str = "android"     # android | ios | web
    model: Optional[str] = None


@router.post("/register")
async def register_device(payload: DeviceRegister, current_user: dict = Depends(get_current_user)):
    """Register or refresh a device push token."""
    db = get_database()
    uid = str(current_user["_id"])
    await db.devices.update_one(
        {"user_id": uid, "token": payload.token},
        {"$set": {"platform": payload.platform, "model": payload.model, "active": True, "updated_at": now()},
         "$setOnInsert": {"created_at": now()}},
        upsert=True,
    )
    return {"message": "Device registered"}


@router.get("")
async def list_devices(current_user: dict = Depends(get_current_user)):
    """List the caller's registered devices."""
    db = get_database()
    rows = await db.devices.find({"user_id": str(current_user["_id"]), "active": True}).to_list(length=100)
    return {"devices": serialize(rows)}


@router.delete("/{device_id}")
async def unregister_device(device_id: str, current_user: dict = Depends(get_current_user)):
    """Unregister a device (e.g. on logout)."""
    db = get_database()
    result = await db.devices.update_one(
        {"_id": oid(device_id), "user_id": str(current_user["_id"])}, {"$set": {"active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device unregistered"}
