"""Games router — mini-game catalog, play sessions and high scores.

Backs the Games page. Games are learning mini-games (letter match, sound catch,
word builder, etc.). Playing a game records a score, awards coins/stars via the
wallet, and feeds per-game leaderboards.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/games", tags=["games"])

# Built-in game catalog seeded on first request if the collection is empty.
DEFAULT_GAMES = [
    {"slug": "letter-match", "title": "Letter Match", "description": "Match Tamil letters to their sounds.", "category": "letters", "difficulty": "easy", "coin_reward": 10, "icon": "🔤"},
    {"slug": "sound-catch", "title": "Sound Catch", "description": "Catch the falling correct sounds.", "category": "phonics", "difficulty": "medium", "coin_reward": 15, "icon": "🎯"},
    {"slug": "word-builder", "title": "Word Builder", "description": "Build words from syllables.", "category": "words", "difficulty": "medium", "coin_reward": 20, "icon": "🧱"},
    {"slug": "breath-balloon", "title": "Breath Balloon", "description": "Blow to inflate the balloon (airflow control).", "category": "breath", "difficulty": "easy", "coin_reward": 12, "icon": "🎈"},
    {"slug": "memory-flip", "title": "Memory Flip", "description": "Flip and match picture-word pairs.", "category": "memory", "difficulty": "hard", "coin_reward": 25, "icon": "🃏"},
    {"slug": "echo-repeat", "title": "Echo Repeat", "description": "Repeat the sound you hear.", "category": "phonics", "difficulty": "easy", "coin_reward": 10, "icon": "🔁"},
]


class ScoreSubmit(BaseModel):
    game_slug: str
    score: int = Field(ge=0)
    duration_sec: Optional[int] = Field(default=None, ge=0)
    accuracy: Optional[float] = Field(default=None, ge=0, le=100)
    level_reached: Optional[int] = None


class GameCreate(BaseModel):
    slug: str
    title: str
    description: str = ""
    category: str = "letters"
    difficulty: str = "easy"
    coin_reward: int = 10
    icon: Optional[str] = None
    active: bool = True


async def _ensure_seeded():
    db = get_database()
    if await db.games.count_documents({}) == 0:
        docs = [{**g, "active": True, "plays": 0, "created_at": now()} for g in DEFAULT_GAMES]
        await db.games.insert_many(docs)


@router.get("")
async def list_games(category: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List active games (seeds the default catalog on first call)."""
    await _ensure_seeded()
    db = get_database()
    query = {"active": True}
    if category:
        query["category"] = category
    games = await db.games.find(query).sort("created_at", 1).to_list(length=200)
    return {"games": serialize(games)}


@router.get("/my-scores")
async def my_scores(current_user: dict = Depends(get_current_user)):
    """Return the caller's best score per game plus totals."""
    db = get_database()
    uid = str(current_user["_id"])
    rows = await db.game_scores.find({"user_id": uid}).to_list(length=100000)
    best = {}
    for r in rows:
        slug = r["game_slug"]
        if slug not in best or r["score"] > best[slug]["score"]:
            best[slug] = {"score": r["score"], "accuracy": r.get("accuracy"), "played_at": r["created_at"].isoformat()}
    return {"total_plays": len(rows), "best_by_game": best}


@router.get("/{game_slug}")
async def game_detail(game_slug: str, current_user: dict = Depends(get_current_user)):
    """Game detail with the caller's personal best."""
    await _ensure_seeded()
    db = get_database()
    game = await db.games.find_one({"slug": game_slug})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    best = await db.game_scores.find_one(
        {"game_slug": game_slug, "user_id": str(current_user["_id"])}, sort=[("score", -1)]
    )
    out = serialize(game)
    out["personal_best"] = best["score"] if best else 0
    return out


@router.post("/score")
async def submit_score(payload: ScoreSubmit, current_user: dict = Depends(get_current_user)):
    """Record a game score and award coins (scaled by score)."""
    db = get_database()
    game = await db.games.find_one({"slug": payload.game_slug})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    uid = str(current_user["_id"])
    doc = {
        "user_id": uid,
        "user_name": current_user.get("child_name") or current_user.get("full_name"),
        "game_slug": payload.game_slug,
        "score": payload.score,
        "duration_sec": payload.duration_sec,
        "accuracy": payload.accuracy,
        "level_reached": payload.level_reached,
        "created_at": now(),
    }
    await db.game_scores.insert_one(doc)
    await db.games.update_one({"slug": payload.game_slug}, {"$inc": {"plays": 1}})

    # Award coins: base reward, bonus for high accuracy.
    coins = int(game.get("coin_reward", 10))
    if payload.accuracy and payload.accuracy >= 80:
        coins += 5
    # Credit wallet (lazy import avoids a circular import at module load).
    from .wallet import credit_wallet
    await credit_wallet(uid, coins=coins, reason=f"Played {game['title']}")

    # Personal best?
    prev_best = await db.game_scores.find_one(
        {"game_slug": payload.game_slug, "user_id": uid, "_id": {"$ne": doc.get("_id")}},
        sort=[("score", -1)],
    )
    is_best = not prev_best or payload.score >= prev_best["score"]
    return {"message": "Score saved", "coins_awarded": coins, "personal_best": is_best}


@router.get("/{game_slug}/leaderboard")
async def game_leaderboard(game_slug: str, limit: int = Query(default=10, ge=1, le=50), current_user: dict = Depends(get_current_user)):
    """Top scores for a single game (best score per user)."""
    db = get_database()
    pipeline = [
        {"$match": {"game_slug": game_slug}},
        {"$sort": {"score": -1}},
        {"$group": {"_id": "$user_id", "user_name": {"$first": "$user_name"}, "score": {"$max": "$score"}}},
        {"$sort": {"score": -1}},
        {"$limit": limit},
    ]
    rows = await db.game_scores.aggregate(pipeline).to_list(length=limit)
    return {"leaderboard": [{"rank": i + 1, "user_name": r.get("user_name"), "score": r["score"]} for i, r in enumerate(rows)]}


# ---- Admin --------------------------------------------------------------------

@router.post("/admin")
async def create_game(payload: GameCreate, current_admin: dict = Depends(require_admin)):
    """Admin: add a game to the catalog."""
    db = get_database()
    if await db.games.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Slug already exists")
    doc = {**payload.model_dump(), "plays": 0, "created_at": now()}
    result = await db.games.insert_one(doc)
    await audit("game.create", current_admin, target=payload.slug)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/admin/{game_slug}")
async def delete_game(game_slug: str, current_admin: dict = Depends(require_admin)):
    """Admin: remove a game."""
    db = get_database()
    result = await db.games.delete_one({"slug": game_slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"message": "Deleted"}
