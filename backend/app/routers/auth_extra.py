"""Auth extras — password reset (OTP), email verification, sessions, refresh."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from datetime import timedelta
import bcrypt
import secrets
from ..database import get_database
from ..utils.jwt_handler import create_access_token, get_current_user
from ..utils.rate_limit import RateLimiter
from ..utils.mongo import serialize, oid, now
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

otp_rate_limit = RateLimiter(times=5, seconds=60)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(min_length=10)


def _hash(value: str) -> str:
    return bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode()


def _check(value: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(value.encode(), hashed.encode())
    except Exception:
        return False


@router.post("/forgot-password", dependencies=[Depends(otp_rate_limit)])
async def forgot_password(payload: ForgotPasswordRequest):
    """Issue a 6-digit OTP for password reset (valid 10 minutes)."""
    db = get_database()
    user = await db.users.find_one({"email": payload.email})
    # Always respond success to avoid leaking which emails exist.
    if not user:
        return {"message": "If that email exists, an OTP has been sent."}
    otp = f"{secrets.randbelow(900000) + 100000}"
    await db.password_resets.delete_many({"email": payload.email})
    await db.password_resets.insert_one({
        "email": payload.email, "otp_hash": _hash(otp),
        "expires_at": now() + timedelta(minutes=10), "used": False, "created_at": now(),
    })
    # A mail provider can be added without changing the public response. Never
    # expose the code on a production deployment.
    result = {"message": "If that email exists, an OTP has been sent."}
    if settings.EXPOSE_DEV_CODES:
        result["dev_otp"] = otp
    return result


@router.post("/verify-otp")
async def verify_otp(payload: VerifyOtpRequest):
    """Verify an OTP without consuming it (used by the verify screen)."""
    db = get_database()
    rec = await db.password_resets.find_one({"email": payload.email, "used": False})
    if not rec or rec["expires_at"] < now() or not _check(payload.otp, rec["otp_hash"]):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    return {"message": "OTP verified", "valid": True}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    """Consume the OTP and set a new password."""
    db = get_database()
    rec = await db.password_resets.find_one({"email": payload.email, "used": False})
    if not rec or rec["expires_at"] < now() or not _check(payload.otp, rec["otp_hash"]):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    await db.users.update_one({"email": payload.email}, {"$set": {"password_hash": _hash(payload.new_password)}})
    await db.password_resets.update_one({"_id": rec["_id"]}, {"$set": {"used": True, "used_at": now()}})
    return {"message": "Password reset successful"}


# ---- Email verification -------------------------------------------------------

@router.post("/verify-email/request")
async def request_email_verification(current_user: dict = Depends(get_current_user)):
    """Send an email-verification OTP for the current user."""
    db = get_database()
    otp = f"{secrets.randbelow(900000) + 100000}"
    await db.email_verifications.delete_many({"user_id": str(current_user["_id"])})
    await db.email_verifications.insert_one({
        "user_id": str(current_user["_id"]), "otp_hash": _hash(otp),
        "expires_at": now() + timedelta(minutes=15), "created_at": now(),
    })
    result = {"message": "Verification code sent"}
    if settings.EXPOSE_DEV_CODES:
        result["dev_otp"] = otp
    return result


@router.post("/verify-email/confirm")
async def confirm_email_verification(payload: dict, current_user: dict = Depends(get_current_user)):
    """Confirm the email-verification OTP and flag the account verified."""
    db = get_database()
    otp = payload.get("otp", "")
    rec = await db.email_verifications.find_one({"user_id": str(current_user["_id"])})
    if not rec or rec["expires_at"] < now() or not _check(otp, rec["otp_hash"]):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": {"email_verified": True, "verified_at": now()}})
    await db.email_verifications.delete_many({"user_id": str(current_user["_id"])})
    return {"message": "Email verified"}


# ---- Sessions & refresh -------------------------------------------------------

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Issue a fresh access token for an already-authenticated user."""
    token = create_access_token(data={"sub": current_user["email"], "role": current_user["role"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List recorded login sessions for this account."""
    db = get_database()
    rows = await db.sessions.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).limit(50).to_list(length=50)
    return {"sessions": serialize(rows)}


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Revoke a specific session record."""
    db = get_database()
    result = await db.sessions.delete_one({"_id": oid(session_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session revoked"}
