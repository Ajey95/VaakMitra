"""Wallet, rewards & shop router.

Backs the Rewards page. Each user has a wallet (coins, gems, stars, XP/level).
Coins are earned from games/sessions and spent in the shop on cosmetic items
(themes, stickers, effects, avatars). Daily rewards and a level curve add
retention mechanics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

# XP required to reach each level (index = level-1). Level 7 is the cap.
LEVEL_CURVE = [0, 100, 250, 500, 900, 1500, 2500]

DEFAULT_SHOP = [
    {"slug": "theme-ocean", "name": "Ocean Theme", "type": "theme", "price_coins": 100, "icon": "🌊"},
    {"slug": "theme-space", "name": "Space Theme", "type": "theme", "price_coins": 150, "icon": "🚀"},
    {"slug": "sticker-star", "name": "Star Sticker Pack", "type": "sticker", "price_coins": 50, "icon": "⭐"},
    {"slug": "sticker-animals", "name": "Animal Stickers", "type": "sticker", "price_coins": 60, "icon": "🐼"},
    {"slug": "effect-confetti", "name": "Confetti Effect", "type": "effect", "price_coins": 80, "icon": "🎉"},
    {"slug": "effect-fireworks", "name": "Fireworks Effect", "type": "effect", "price_coins": 120, "icon": "🎆"},
    {"slug": "avatar-robot", "name": "Robot Avatar", "type": "avatar", "price_coins": 200, "price_gems": 5, "icon": "🤖"},
    {"slug": "avatar-cat", "name": "Cat Avatar", "type": "avatar", "price_coins": 180, "icon": "🐱"},
]


class SpendRequest(BaseModel):
    coins: int = Field(default=0, ge=0)
    gems: int = Field(default=0, ge=0)
    reason: str = "purchase"


class AdminAdjust(BaseModel):
    user_id: str
    coins: int = 0
    gems: int = 0
    stars: int = 0
    reason: str = "admin adjustment"


def _level_for_xp(xp: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_CURVE):
        if xp >= threshold:
            level = i + 1
    return level


async def _get_or_create(user_id: str) -> dict:
    db = get_database()
    w = await db.wallets.find_one({"user_id": user_id})
    if not w:
        w = {"user_id": user_id, "coins": 0, "gems": 0, "stars": 0, "xp": 0, "level": 1,
             "created_at": now(), "updated_at": now()}
        await db.wallets.insert_one(w)
    return w


async def _txn(user_id: str, coins: int, gems: int, stars: int, xp: int, reason: str, kind: str):
    db = get_database()
    await db.wallet_transactions.insert_one({
        "user_id": user_id, "coins": coins, "gems": gems, "stars": stars, "xp": xp,
        "reason": reason, "kind": kind, "created_at": now(),
    })


async def credit_wallet(user_id: str, coins: int = 0, gems: int = 0, stars: int = 0, xp: int = None, reason: str = "reward"):
    """Public helper: credit a wallet (used by games, sessions, achievements)."""
    db = get_database()
    await _get_or_create(user_id)
    if xp is None:
        xp = coins  # coins double as XP by default
    w = await db.wallets.find_one({"user_id": user_id})
    new_xp = w.get("xp", 0) + xp
    new_level = _level_for_xp(new_xp)
    await db.wallets.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": coins, "gems": gems, "stars": stars, "xp": xp},
         "$set": {"level": new_level, "updated_at": now()}},
    )
    await _txn(user_id, coins, gems, stars, xp, reason, "credit")
    return {"level": new_level, "leveled_up": new_level > w.get("level", 1)}


@router.get("")
async def get_wallet(current_user: dict = Depends(get_current_user)):
    """Return the caller's wallet with level progress to the next level."""
    w = await _get_or_create(str(current_user["_id"]))
    level = w.get("level", 1)
    next_threshold = LEVEL_CURVE[level] if level < len(LEVEL_CURVE) else None
    current_threshold = LEVEL_CURVE[level - 1]
    out = serialize(w)
    out["next_level_xp"] = next_threshold
    out["level_progress"] = (
        round((w.get("xp", 0) - current_threshold) / (next_threshold - current_threshold) * 100, 1)
        if next_threshold else 100.0
    )
    out["max_level"] = len(LEVEL_CURVE)
    return out


@router.get("/transactions")
async def transactions(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Paginated wallet transaction history."""
    db = get_database()
    return await paginate(db.wallet_transactions, {"user_id": str(current_user["_id"])}, page, limit)


@router.post("/daily-reward")
async def daily_reward(current_user: dict = Depends(get_current_user)):
    """Claim a once-per-day coin reward with a growing streak bonus."""
    db = get_database()
    uid = str(current_user["_id"])
    w = await _get_or_create(uid)
    last = w.get("last_daily_claim")
    today = now().date()
    if last and last.date() == today:
        raise HTTPException(status_code=409, detail="Already claimed today")
    # Streak: consecutive-day bonus.
    streak = w.get("daily_streak", 0)
    if last and last.date() == today - timedelta(days=1):
        streak += 1
    else:
        streak = 1
    reward = 20 + min(streak, 7) * 5
    await db.wallets.update_one(
        {"user_id": uid},
        {"$inc": {"coins": reward, "xp": reward},
         "$set": {"last_daily_claim": now(), "daily_streak": streak, "updated_at": now()}},
    )
    await _txn(uid, reward, 0, 0, reward, f"Daily reward (streak {streak})", "credit")
    return {"message": "Daily reward claimed", "coins": reward, "streak": streak}


# ---- Shop ---------------------------------------------------------------------

@router.get("/shop")
async def shop(type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List shop items; flags which the caller already owns."""
    db = get_database()
    if await db.shop_items.count_documents({}) == 0:
        await db.shop_items.insert_many([{**s, "active": True, "created_at": now()} for s in DEFAULT_SHOP])
    query = {"active": True}
    if type:
        query["type"] = type
    items = await db.shop_items.find(query).to_list(length=200)
    owned = {i["item_slug"] for i in await db.inventory.find({"user_id": str(current_user["_id"])}).to_list(length=1000)}
    out = serialize(items)
    for i in out:
        i["owned"] = i["slug"] in owned
    return {"items": out}


@router.post("/shop/{item_slug}/buy")
async def buy(item_slug: str, current_user: dict = Depends(get_current_user)):
    """Purchase a shop item, debiting coins/gems and adding to inventory."""
    db = get_database()
    uid = str(current_user["_id"])
    item = await db.shop_items.find_one({"slug": item_slug, "active": True})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if await db.inventory.find_one({"user_id": uid, "item_slug": item_slug}):
        raise HTTPException(status_code=409, detail="Already owned")
    w = await _get_or_create(uid)
    price_coins = item.get("price_coins", 0)
    price_gems = item.get("price_gems", 0)
    if w.get("coins", 0) < price_coins or w.get("gems", 0) < price_gems:
        raise HTTPException(status_code=402, detail="Not enough balance")
    await db.wallets.update_one(
        {"user_id": uid}, {"$inc": {"coins": -price_coins, "gems": -price_gems}, "$set": {"updated_at": now()}}
    )
    await _txn(uid, -price_coins, -price_gems, 0, 0, f"Bought {item['name']}", "debit")
    await db.inventory.insert_one({
        "user_id": uid, "item_slug": item_slug, "name": item["name"], "type": item["type"],
        "equipped": False, "acquired_at": now(),
    })
    return {"message": "Purchase successful", "item": item["name"]}


@router.get("/inventory")
async def inventory(current_user: dict = Depends(get_current_user)):
    """List items the caller owns."""
    db = get_database()
    items = await db.inventory.find({"user_id": str(current_user["_id"])}).to_list(length=1000)
    return {"items": serialize(items)}


@router.post("/inventory/{item_slug}/equip")
async def equip(item_slug: str, current_user: dict = Depends(get_current_user)):
    """Equip an owned item (unequips others of the same type)."""
    db = get_database()
    uid = str(current_user["_id"])
    item = await db.inventory.find_one({"user_id": uid, "item_slug": item_slug})
    if not item:
        raise HTTPException(status_code=404, detail="Item not owned")
    await db.inventory.update_many({"user_id": uid, "type": item["type"]}, {"$set": {"equipped": False}})
    await db.inventory.update_one({"user_id": uid, "item_slug": item_slug}, {"$set": {"equipped": True}})
    return {"message": f"{item['name']} equipped"}


# ---- Admin --------------------------------------------------------------------

@router.post("/admin/adjust")
async def admin_adjust(payload: AdminAdjust, current_admin: dict = Depends(require_admin)):
    """Admin: grant or deduct currency from a user's wallet."""
    await credit_wallet(payload.user_id, payload.coins, payload.gems, payload.stars, reason=payload.reason)
    await audit("wallet.adjust", current_admin, target=payload.user_id,
                meta={"coins": payload.coins, "gems": payload.gems, "stars": payload.stars})
    return {"message": "Wallet adjusted"}
