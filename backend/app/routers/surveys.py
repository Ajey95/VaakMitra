"""Surveys router — multi-question surveys with responses & results.

Admins publish surveys (onboarding, satisfaction); users respond once; admins
view aggregated results.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Any
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/surveys", tags=["surveys"])


class SurveyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    questions: List[dict] = Field(description="[{id, prompt, kind: single|multi|text, options?}]")


class SurveyResponse(BaseModel):
    answers: List[Any]


@router.get("")
async def list_surveys(current_user: dict = Depends(get_current_user)):
    """List active surveys, flagging which the caller has completed."""
    db = get_database()
    uid = str(current_user["_id"])
    surveys = await db.surveys.find({"active": True}).sort("created_at", -1).to_list(length=100)
    done = {r["survey_id"] for r in await db.survey_responses.find({"user_id": uid}).to_list(length=500)}
    out = []
    for s in surveys:
        item = serialize(s)
        item["completed"] = str(s["_id"]) in done
        out.append(item)
    return {"surveys": out}


@router.get("/{survey_id}")
async def get_survey(survey_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a survey to complete."""
    db = get_database()
    s = await db.surveys.find_one({"_id": oid(survey_id), "active": True})
    if not s:
        raise HTTPException(status_code=404, detail="Survey not found")
    return serialize(s)


@router.post("/{survey_id}/respond")
async def respond(survey_id: str, payload: SurveyResponse, current_user: dict = Depends(get_current_user)):
    """Submit a survey response (once per user)."""
    db = get_database()
    uid = str(current_user["_id"])
    s = await db.surveys.find_one({"_id": oid(survey_id), "active": True})
    if not s:
        raise HTTPException(status_code=404, detail="Survey not found")
    if await db.survey_responses.find_one({"user_id": uid, "survey_id": survey_id}):
        raise HTTPException(status_code=409, detail="Already responded")
    await db.survey_responses.insert_one({"user_id": uid, "survey_id": survey_id, "answers": payload.answers, "created_at": now()})
    return {"message": "Response recorded"}


@router.post("/admin")
async def create_survey(payload: SurveyCreate, current_admin: dict = Depends(require_admin)):
    """Admin: create a survey."""
    db = get_database()
    doc = {**payload.model_dump(), "active": True, "created_at": now()}
    result = await db.surveys.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/admin/{survey_id}/results")
async def results(survey_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: aggregate results for a survey."""
    db = get_database()
    s = await db.surveys.find_one({"_id": oid(survey_id)})
    if not s:
        raise HTTPException(status_code=404, detail="Survey not found")
    responses = await db.survey_responses.find({"survey_id": survey_id}).to_list(length=100000)
    tally = []
    for i, q in enumerate(s.get("questions", [])):
        if q.get("kind") in ("single", "multi") and q.get("options"):
            counts = {opt: 0 for opt in q["options"]}
            for r in responses:
                ans = r["answers"][i] if i < len(r["answers"]) else None
                for a in (ans if isinstance(ans, list) else [ans]):
                    if isinstance(a, int) and 0 <= a < len(q["options"]):
                        counts[q["options"][a]] += 1
                    elif a in counts:
                        counts[a] += 1
            tally.append({"question": q.get("prompt"), "counts": counts})
        else:
            tally.append({"question": q.get("prompt"), "text_answers": [r["answers"][i] for r in responses if i < len(r["answers"])]})
    return {"survey": s.get("title"), "response_count": len(responses), "results": tally}


@router.delete("/admin/{survey_id}")
async def delete_survey(survey_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a survey and its responses."""
    db = get_database()
    result = await db.surveys.delete_one({"_id": oid(survey_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Survey not found")
    await db.survey_responses.delete_many({"survey_id": survey_id})
    return {"message": "Deleted"}
