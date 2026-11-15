"""Uploads router for durable user media."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from ..config import settings
from ..database import get_database
from ..services.media_storage import get_media_storage
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED = {"image/png", "image/jpeg", "image/webp", "image/gif", "audio/wav", "audio/webm", "audio/mpeg", "application/pdf"}


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form(default="general"),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to Cloudinary in production or local disk in development."""
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    try:
        storage = get_media_storage()
        stored = await storage.save(data, file.filename or "upload", file.content_type or "application/octet-stream", str(current_user["_id"]), purpose)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db = get_database()
    doc = {
        "user_id": str(current_user["_id"]), "original_name": file.filename, **stored,
        "content_type": file.content_type, "size": len(data), "purpose": purpose,
        "created_at": now(),
    }
    result = await db.uploads.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def my_uploads(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """List the caller's uploads."""
    db = get_database()
    return await paginate(db.uploads, {"user_id": str(current_user["_id"])}, page, limit)


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an uploaded file (and its metadata)."""
    db = get_database()
    doc = await db.uploads.find_one({"_id": oid(upload_id), "user_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Upload not found")
    try:
        await get_media_storage().delete(doc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    await db.uploads.delete_one({"_id": oid(upload_id)})
    return {"message": "Deleted"}
