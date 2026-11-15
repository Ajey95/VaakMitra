"""Assessment router — quizzes, attempts and scoring.

Backs the Assessment page (6 quiz types: letter, image, voice, pronunciation,
video, tongue). Admins/therapists author quizzes; users take them; attempts are
scored server-side and stored for progress tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin, require_therapist
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/assessment", tags=["assessment"])

QUIZ_TYPES = ["letter", "image", "voice", "pronunciation", "video", "tongue", "mixed"]

DEFAULT_QUIZZES = [
    {
        "slug": "tamil-vowels", "title": "Tamil Vowels Quiz", "type": "letter",
        "description": "Identify Tamil vowel letters.", "difficulty": "easy", "coin_reward": 30,
        "questions": [
            {"id": "q1", "prompt": "Which letter is 'அ'?", "options": ["அ", "ஆ", "இ", "ஈ"], "answer": 0},
            {"id": "q2", "prompt": "Which letter is 'ஆ'?", "options": ["அ", "ஆ", "உ", "எ"], "answer": 1},
            {"id": "q3", "prompt": "Which letter is 'இ'?", "options": ["ஈ", "அ", "இ", "ஐ"], "answer": 2},
        ],
    },
    {
        "slug": "picture-words", "title": "Picture Words", "type": "image",
        "description": "Match the picture to the correct word.", "difficulty": "medium", "coin_reward": 40,
        "questions": [
            {"id": "q1", "prompt": "🐘 is called?", "options": ["யானை", "பூனை", "நாய்", "மாடு"], "answer": 0},
            {"id": "q2", "prompt": "🍎 is called?", "options": ["வாழை", "ஆப்பிள்", "மா", "எலுமிச்சை"], "answer": 1},
        ],
    },
]


class AttemptSubmit(BaseModel):
    quiz_slug: str
    answers: List[Any] = Field(description="Selected option index per question, in order")
    duration_sec: Optional[int] = None


class QuizCreate(BaseModel):
    slug: str
    title: str
    type: str = "mixed"
    description: str = ""
    difficulty: str = "easy"
    coin_reward: int = 30
    questions: List[dict] = []
    active: bool = True


async def _ensure_seeded():
    db = get_database()
    if await db.quizzes.count_documents({}) == 0:
        await db.quizzes.insert_many([{**q, "active": True, "attempts": 0, "created_at": now()} for q in DEFAULT_QUIZZES])


def _public_quiz(quiz: dict) -> dict:
    """Strip answer keys before sending a quiz to the client."""
    out = serialize(quiz)
    for q in out.get("questions", []):
        q.pop("answer", None)
    return out


@router.get("")
async def list_quizzes(type: Optional[str] = None, difficulty: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List available quizzes (answer keys hidden)."""
    await _ensure_seeded()
    db = get_database()
    query = {"active": True}
    if type in QUIZ_TYPES:
        query["type"] = type
    if difficulty:
        query["difficulty"] = difficulty
    quizzes = await db.quizzes.find(query).to_list(length=200)
    out = []
    for q in quizzes:
        item = _public_quiz(q)
        item["question_count"] = len(q.get("questions", []))
        item.pop("questions", None)  # list view omits questions
        out.append(item)
    return {"quizzes": out}


@router.get("/{quiz_slug}")
async def get_quiz(quiz_slug: str, current_user: dict = Depends(get_current_user)):
    """Fetch a quiz to take (answer keys stripped)."""
    await _ensure_seeded()
    db = get_database()
    quiz = await db.quizzes.find_one({"slug": quiz_slug, "active": True})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return _public_quiz(quiz)


@router.post("/submit")
async def submit_attempt(payload: AttemptSubmit, current_user: dict = Depends(get_current_user)):
    """Score an attempt server-side, store it and award coins on a pass."""
    db = get_database()
    quiz = await db.quizzes.find_one({"slug": payload.quiz_slug})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = quiz.get("questions", [])
    total = len(questions)
    correct = 0
    review = []
    for i, q in enumerate(questions):
        given = payload.answers[i] if i < len(payload.answers) else None
        is_correct = given == q.get("answer")
        correct += 1 if is_correct else 0
        review.append({"id": q.get("id"), "correct": is_correct, "your_answer": given, "answer": q.get("answer")})
    score_pct = round(correct / total * 100, 1) if total else 0
    passed = score_pct >= 60

    uid = str(current_user["_id"])
    attempt = {
        "user_id": uid, "quiz_slug": payload.quiz_slug, "quiz_title": quiz.get("title"),
        "type": quiz.get("type"), "correct": correct, "total": total, "score_pct": score_pct,
        "passed": passed, "duration_sec": payload.duration_sec, "created_at": now(),
    }
    result = await db.quiz_attempts.insert_one(attempt)
    await db.quizzes.update_one({"slug": payload.quiz_slug}, {"$inc": {"attempts": 1}})

    coins = 0
    if passed:
        coins = int(quiz.get("coin_reward", 30))
        if score_pct == 100:
            coins += 10
        from .wallet import credit_wallet
        await credit_wallet(uid, coins=coins, reason=f"Passed {quiz.get('title')}")

    return {
        "attempt_id": str(result.inserted_id), "correct": correct, "total": total,
        "score_pct": score_pct, "passed": passed, "coins_awarded": coins, "review": review,
    }


@router.get("/attempts/history")
async def attempt_history(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Paginated history of the caller's quiz attempts."""
    db = get_database()
    return await paginate(db.quiz_attempts, {"user_id": str(current_user["_id"])}, page, limit)


@router.get("/attempts/best")
async def best_attempts(current_user: dict = Depends(get_current_user)):
    """Best score per quiz for the caller."""
    db = get_database()
    pipeline = [
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {"_id": "$quiz_slug", "quiz_title": {"$first": "$quiz_title"},
                    "best": {"$max": "$score_pct"}, "attempts": {"$sum": 1}}},
    ]
    rows = await db.quiz_attempts.aggregate(pipeline).to_list(length=500)
    return {"best": [{"quiz_slug": r["_id"], "quiz_title": r["quiz_title"], "best_score": r["best"], "attempts": r["attempts"]} for r in rows]}


# ---- Authoring (therapist/admin) ---------------------------------------------

@router.post("/admin")
async def create_quiz(payload: QuizCreate, current_user: dict = Depends(require_therapist)):
    """Therapist/Admin: author a quiz (with answer keys)."""
    db = get_database()
    if await db.quizzes.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Slug exists")
    doc = {**payload.model_dump(), "attempts": 0, "author": current_user.get("full_name"), "created_at": now()}
    result = await db.quizzes.insert_one(doc)
    await audit("quiz.create", current_user, target=payload.slug)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.patch("/admin/{quiz_slug}")
async def update_quiz(quiz_slug: str, payload: dict, current_user: dict = Depends(require_therapist)):
    """Therapist/Admin: update a quiz."""
    db = get_database()
    payload.pop("_id", None)
    payload.pop("slug", None)
    payload["updated_at"] = now()
    result = await db.quizzes.update_one({"slug": quiz_slug}, {"$set": payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return serialize(await db.quizzes.find_one({"slug": quiz_slug}))


@router.delete("/admin/{quiz_slug}")
async def delete_quiz(quiz_slug: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a quiz."""
    db = get_database()
    result = await db.quizzes.delete_one({"slug": quiz_slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return {"message": "Deleted"}
