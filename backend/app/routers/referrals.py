"""Referrals router — refer-a-friend with codes and rewards.

Each user has a referral code; when a new user redeems it, both sides earn
coins. Backs the app's "Refer friends" flow.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import secrets
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, now

router = APIRouter(prefix="/api/referrals", tags=["referrals"])

REFERRER_REWARD = 100
REFEREE_REWARD = 50


class RedeemRequest(BaseModel):
    code: str = Field(min_length=4, max_length=20)


def _gen_code(name: str) -> str:
    prefix = "".join(c for c in (name or "SE").upper() if c.isalpha())[:4] or "SE"
    return f"{prefix}{secrets.randbelow(9000) + 1000}"


@router.get("/my-code")
async def my_code(current_user: dict = Depends(get_current_user)):
    """Return (creating if needed) the caller's referral code + stats."""
    db = get_database()
    uid = str(current_user["_id"])
    rec = await db.referral_codes.find_one({"user_id": uid})
    if not rec:
        code = _gen_code(current_user.get("full_name"))
        while await db.referral_codes.find_one({"code": code}):
            code = _gen_code(current_user.get("full_name"))
        rec = {"user_id": uid, "code": code, "uses": 0, "coins_earned": 0, "created_at": now()}
        await db.referral_codes.insert_one(rec)
    return serialize(rec)


@router.post("/redeem")
async def redeem(payload: RedeemRequest, current_user: dict = Depends(get_current_user)):
    """Redeem someone's referral code (once per account)."""
    db = get_database()
    uid = str(current_user["_id"])
    if await db.referral_redemptions.find_one({"user_id": uid}):
        raise HTTPException(status_code=409, detail="You have already redeemed a referral code")
    rec = await db.referral_codes.find_one({"code": payload.code.upper()})
    if not rec:
        raise HTTPException(status_code=404, detail="Invalid code")
    if rec["user_id"] == uid:
        raise HTTPException(status_code=400, detail="Cannot redeem your own code")
    await db.referral_redemptions.insert_one({"user_id": uid, "code": payload.code.upper(), "referrer_id": rec["user_id"], "created_at": now()})
    await db.referral_codes.update_one({"_id": rec["_id"]}, {"$inc": {"uses": 1, "coins_earned": REFERRER_REWARD}})
    from .wallet import credit_wallet
    await credit_wallet(rec["user_id"], coins=REFERRER_REWARD, reason="Referral bonus")
    await credit_wallet(uid, coins=REFEREE_REWARD, reason="Welcome referral bonus")
    return {"message": "Referral redeemed!", "coins_awarded": REFEREE_REWARD}


@router.get("/history")
async def history(current_user: dict = Depends(get_current_user)):
    """List who redeemed the caller's code."""
    db = get_database()
    uid = str(current_user["_id"])
    rows = await db.referral_redemptions.find({"referrer_id": uid}).sort("created_at", -1).to_list(length=500)
    out = []
    for r in rows:
        u = await db.users.find_one({"_id": __import__("bson").ObjectId(r["user_id"])}) if r.get("user_id") else None
        out.append({"redeemed_by": (u.get("full_name") if u else "A friend"), "at": r["created_at"].isoformat()})
    return {"referrals": out, "count": len(out)}


@router.get("/leaderboard")
async def leaderboard(current_user: dict = Depends(get_current_user)):
    """Top referrers by number of successful referrals."""
    db = get_database()
    rows = await db.referral_codes.find({"uses": {"$gt": 0}}).sort("uses", -1).limit(10).to_list(length=10)
    board = []
    for i, r in enumerate(rows):
        u = await db.users.find_one({"_id": __import__("bson").ObjectId(r["user_id"])})
        board.append({"rank": i + 1, "name": (u.get("full_name") if u else "Ambassador"), "referrals": r["uses"], "coins": r["coins_earned"]})
    return {"leaderboard": board}
