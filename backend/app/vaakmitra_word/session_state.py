"""Server-owned word sessions and single-document attempt claims (SSOT 13.1/14.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument

from ..config import settings
from ..utils.mongo import oid
from .assessment import AssessmentContext
from .contracts import AssessmentResult, Decision, ReasonCode
from .policy import TherapistConstraints
from .report_access import report_share_allowed
from .session_limits import SessionLimits
from .session_report import build_session_summary
from .vocabulary import VocabularyRegistry


@dataclass(frozen=True)
class SessionClaim:
    assessment: AssessmentContext
    current_index: int
    word_count: int
    claim_token: str = ''


class WordSessionStore:
    def __init__(self, db, vocabulary: VocabularyRegistry, clock=None):
        self.db = db
        self.sessions = db.word_sessions
        self.vocabulary = vocabulary
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _utc(value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    async def _load(self, session_id, actor):
        session = await self.sessions.find_one({"_id": session_id})
        if session is None:
            raise HTTPException(404, detail="word_session_not_found")
        if not self._authorized(session, actor):
            raise HTTPException(403, detail="word_session_access_denied")
        return session

    def _limits(self, session):
        try:
            return SessionLimits.model_validate(session["session_limits"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(409, detail="word_plan_limits_required") from exc

    async def _enforce_lifetime(self, session):
        limits = self._limits(session)
        created = session.get("created_at")
        if not isinstance(created, datetime):
            raise HTTPException(409, detail="word_session_created_time_missing")
        if ((self.clock() - self._utc(created)).total_seconds() >= limits.max_session_seconds
                or session.get("total_attempts", 0) >= limits.max_total_attempts):
            await self.sessions.update_one(
                {"_id": session["_id"], "status": {"$in": ["active", "paused"]}},
                {"$set": {"status": "expired", "inflight_attempt_id": None,
                          "inflight_claim_token": None,
                          "ended_at": self.clock(), "restart_after": self.clock() + timedelta(seconds=limits.break_seconds)}},
            )
            raise HTTPException(409, detail="word_session_limit_reached")
        lease = session.get("lease_expires_at")
        if session.get("inflight_attempt_id") and isinstance(lease, datetime) and self._utc(lease) <= self.clock():
            await self.sessions.update_one(
                {"_id": session["_id"], "inflight_attempt_id": session["inflight_attempt_id"]},
                {"$set": {"status": "paused", "inflight_attempt_id": None,
                          "inflight_claim_token": None,
                          "pause_reason": "model_timeout", "paused_at": self.clock()},
                 "$addToSet": {"completed_attempt_ids": session["inflight_attempt_id"]}},
            )
            raise HTTPException(409, detail="word_attempt_lease_expired")
        return limits

    @staticmethod
    def _authorized(session: dict, actor: dict) -> bool:
        actor_id = str(actor["_id"])
        return (actor.get("role") == "admin"
                or actor.get("role") == "user" and actor_id == session.get("owner_id")
                or actor.get("role") == "therapist" and actor_id == session.get("therapist_id"))

    async def _require_current_plan(self, session: dict) -> None:
        plan_id, owner_id = session.get("plan_id"), session.get("owner_id")
        plan = await self.db.treatment_plans.find_one({"_id": oid(plan_id)}) if plan_id else None
        child = await self.db.users.find_one({"_id": oid(owner_id)}) if owner_id else None
        if (not plan or plan.get("status") != "active" or not child or child.get("role") != "user"
                or plan.get("child_id") != owner_id
                or plan.get("therapist_id") != session.get("therapist_id")
                or child.get("therapist_id") != session.get("therapist_id")
                or plan.get("word_ids") != session.get("word_ids")
                or plan.get("session_limits") != session.get("session_limits")
                or plan.get("vocabulary_version") != session.get("vocabulary_version")):
            raise HTTPException(status_code=409, detail="word_session_plan_revoked")

    async def claim(self, session_id: str, attempt_id: str, word_id: str, target_word: str,
                    exercise_version: str, actor: dict) -> SessionClaim:
        session = await self.sessions.find_one({"_id": session_id})
        if session is None:
            raise HTTPException(status_code=404, detail="word_session_not_found")
        if not self._authorized(session, actor):
            raise HTTPException(status_code=403, detail="word_session_access_denied")
        await self._require_current_plan(session)
        limits = await self._enforce_lifetime(session)
        words = session.get("word_ids") or []
        index = session.get("current_index", 0)
        if (session.get("vocabulary_version") != self.vocabulary.version
                or not isinstance(index, int) or index < 0 or index >= len(words)):
            raise HTTPException(status_code=409, detail="word_session_plan_unavailable")
        registered = next((entry for entry in self.vocabulary.entries if entry.word_id == words[index]), None)
        if registered is None:
            raise HTTPException(status_code=409, detail="word_session_plan_unavailable")
        if (word_id != registered.word_id or target_word.strip() != registered.canonical_tamil
                or exercise_version != session["vocabulary_version"]):
            raise HTTPException(status_code=422, detail="word_not_assigned_to_session")
        claim_token = uuid4().hex
        # SES-003/005: this legacy-named set reserves consumed IDs at claim time,
        # including canceled/inflight captures; completed totals come from attempts.
        previous = await self.sessions.find_one_and_update(
            {"_id": session_id, "status": "active", "inflight_attempt_id": None,
             "current_index": index, "attempt_count": session["attempt_count"],
             "total_attempts": session.get("total_attempts", 0),
             "completed_attempt_ids": {"$ne": attempt_id}},
            {"$set": {"inflight_attempt_id": attempt_id,
                      "inflight_claim_token": claim_token,
                      "lease_expires_at": self.clock() + timedelta(seconds=settings.VAAKMITRA_INFERENCE_TIMEOUT_SECONDS + 5)},
             "$inc": {"total_attempts": 1},
             "$addToSet": {"completed_attempt_ids": attempt_id}},
            return_document=ReturnDocument.BEFORE,
        )
        if previous is None:
            raise HTTPException(status_code=409, detail="word_attempt_conflict")
        next_word_id = words[index + 1] if index + 1 < len(words) else ""
        allowed = ("repeat", "picture", "next_word", "break", "safe_end") if next_word_id else (
            "repeat", "picture", "break", "safe_end")
        assessment = AssessmentContext(
            session_id=session_id, attempt_id=attempt_id,
            word_id=registered.word_id, target_word=registered.canonical_tamil,
            attempt_count=previous["attempt_count"],
            therapist_constraints=TherapistConstraints(allowed_actions=allowed, next_exercise_id=next_word_id,
                                                       max_retries=limits.max_retries),
        )
        return SessionClaim(assessment=assessment, current_index=index,
                            word_count=len(words), claim_token=claim_token)

    async def complete(self, claim: SessionClaim, result: AssessmentResult) -> AssessmentResult:
        context = claim.assessment
        if (result.session_id, result.attempt_id, result.word_id) != (
            context.session_id, context.attempt_id, context.word_id
        ):
            raise ValueError("assessment result does not match claimed attempt")
        latest = await self.sessions.find_one({"_id": context.session_id})
        if latest is not None:
            try:
                await self._require_current_plan(latest)
            except HTTPException:
                await self.sessions.update_one(
                    {"_id": context.session_id, "status": "active", "inflight_attempt_id": context.attempt_id,
                     "inflight_claim_token": claim.claim_token},
                    {"$set": {"status": "paused", "inflight_attempt_id": None,
                              "inflight_claim_token": None},
                     "$addToSet": {"completed_attempt_ids": context.attempt_id}},
                )
                return AssessmentResult.unscorable(
                    ReasonCode.CANCELLED, session_id=context.session_id, attempt_id=context.attempt_id,
                    word_id=context.word_id, target_word=context.target_word)
        if latest is None:
            return self._cancelled(context)
        limits = self._limits(latest)
        lease = latest.get("lease_expires_at")
        expired = ((self.clock() - self._utc(latest["created_at"])).total_seconds() >= limits.max_session_seconds
                   or isinstance(lease, datetime) and self._utc(lease) <= self.clock())
        if expired:
            await self.stop(context.session_id, {"_id": latest["owner_id"], "role": "user"})
            return self._cancelled(context)
        next_index = claim.current_index + (1 if result.decision is Decision.PASS else 0)
        status = "complete" if next_index == claim.word_count else "active"
        if result.decision is Decision.UNSCORABLE and result.reason_code in {
            ReasonCode.MODEL_UNAVAILABLE, ReasonCode.CALIBRATION_UNAVAILABLE,
            ReasonCode.ARTIFACT_MISMATCH, ReasonCode.MODEL_INTEGRITY_MISMATCH,
            ReasonCode.MODEL_TIMEOUT, ReasonCode.MODEL_INFERENCE_FAILED,
            ReasonCode.VAD_UNAVAILABLE, ReasonCode.CLASSIFIER_UNAVAILABLE, ReasonCode.REFERENCE_UNAVAILABLE,
        }:
            status = "paused"
        if (result.decision is Decision.RETRY
                and claim.assessment.attempt_count >= claim.assessment.therapist_constraints.max_retries):
            status = "paused"
        retries = (claim.assessment.attempt_count + 1 if result.decision is Decision.RETRY
                   else claim.assessment.attempt_count if result.decision is Decision.UNSCORABLE else 0)
        if latest.get("total_attempts", 0) >= limits.max_total_attempts:
            status = "complete"
            result = result.model_copy(update={"response_intent": "OFFER_BREAK", "avatar_state": "BREAK", "next_exercise_id": None})
        event = {"attempt_id": context.attempt_id, "word_id": context.word_id,
                 "decision": result.decision.value, "reason_code": result.reason_code.value,
                 "response_intent": result.response_intent, "avatar_state": result.avatar_state,
                 "model_version": result.model_version, "classifier_version": result.classifier_version,
                 "reference_bank_version": result.reference_bank_version, "calibration_version": result.calibration_version,
                 "policy_version": result.policy_version, "created_at": self.clock()}
        changes = {"status": status, "current_index": next_index,
                   "attempt_count": retries, "inflight_attempt_id": None,
                   "inflight_claim_token": None,
                   "last_reason_code": result.reason_code.value}
        if status == "paused":
            changes.update(paused_at=self.clock(), pause_reason="retry_limit" if result.decision is Decision.RETRY else "capability")
        if status == "complete":
            changes.update(ended_at=self.clock(), restart_after=self.clock() + timedelta(seconds=limits.break_seconds))
        updated = await self.sessions.update_one(
            {"_id": context.session_id, "status": "active", "inflight_attempt_id": context.attempt_id,
             "inflight_claim_token": claim.claim_token,
             "current_index": claim.current_index},
            {"$set": changes, "$push": {"attempts": event},
             "$addToSet": {"completed_attempt_ids": context.attempt_id}},
        )
        if updated.modified_count != 1:
            return AssessmentResult.unscorable(
                ReasonCode.CANCELLED, session_id=context.session_id, attempt_id=context.attempt_id,
                word_id=context.word_id, target_word=context.target_word)
        return result

    @staticmethod
    def _cancelled(context):
        return AssessmentResult.unscorable(ReasonCode.CANCELLED, session_id=context.session_id,
            attempt_id=context.attempt_id, word_id=context.word_id, target_word=context.target_word).model_copy(
                update={"response_intent": "CALM_END", "avatar_state": "END"})

    async def stop(self, session_id: str, actor: dict, *, reason: str = "user_stop") -> dict:
        session = await self.sessions.find_one({"_id": session_id})
        if session is None:
            raise HTTPException(status_code=404, detail="word_session_not_found")
        if not self._authorized(session, actor):
            raise HTTPException(status_code=403, detail="word_session_access_denied")
        try:
            limits = self._limits(session)
        except HTTPException:
            # SES-003: malformed legacy configuration must never disable Stop.
            limits = SessionLimits()
        await self.sessions.update_one(
            {"_id": session_id, "status": {"$ne": "ended"}},
            {"$set": {"status": "ended", "inflight_attempt_id": None,
                      "inflight_claim_token": None, "ended_at": self.clock(),
                      "restart_after": self.clock() + timedelta(seconds=limits.break_seconds)},
             "$push": {"session_events": {"type": "session_ended", "reason": reason,
                                          "at": self.clock()}}},
        )
        return {"session_id": session_id, "status": "ended"}

    async def pause(self, session_id: str, actor: dict):
        session = await self._load(session_id, actor)
        await self._require_current_plan(session)
        if session["status"] not in ("active", "paused"):
            raise HTTPException(409, detail="word_session_not_active")
        change = {"$set": {"status": "paused", "inflight_attempt_id": None,
                           "inflight_claim_token": None,
                           "paused_at": self.clock(), "pause_reason": "user_pause"},
                  "$push": {"session_events": {"type": "break_started", "reason": "user_pause",
                                               "at": self.clock()}}}
        if session.get("inflight_attempt_id"):
            change["$addToSet"] = {"completed_attempt_ids": session["inflight_attempt_id"]}
        # Do not overwrite an existing retry/capability break with an easier resume reason.
        await self.sessions.update_one({"_id": session_id, "status": "active"}, change)
        return await self.snapshot(session_id, actor)

    async def resume(self, session_id: str, actor: dict, *, next_word_id=None):
        session = await self._load(session_id, actor)
        voluntary_owner_break = (actor.get("role") == "user"
                                 and session.get("pause_reason") == "user_pause"
                                 and next_word_id is None)
        if actor.get("role") not in ("admin", "therapist") and not voluntary_owner_break:
            raise HTTPException(403, detail="adult_continuation_required")
        await self._require_current_plan(session)
        limits = await self._enforce_lifetime(session)
        if session["status"] != "paused":
            raise HTTPException(409, detail="word_session_not_paused")
        if voluntary_owner_break:
            paused_at = session.get("paused_at")
            if not isinstance(paused_at, datetime) or (self.clock() - self._utc(paused_at)).total_seconds() < limits.break_seconds:
                raise HTTPException(409, detail="completed_break_required")
        index = session["current_index"]
        if next_word_id is not None:
            if next_word_id not in session["word_ids"]:
                raise HTTPException(422, detail="word_not_assigned_to_session")
            index = session["word_ids"].index(next_word_id)
        if session.get("pause_reason") == "retry_limit":
            elapsed = (self.clock() - self._utc(session["paused_at"])).total_seconds()
            if elapsed < limits.break_seconds or index == session["current_index"]:
                raise HTTPException(409, detail="completed_break_and_other_assigned_word_required")
        updated = await self.sessions.update_one(
            {"_id": session_id, "status": "paused", "current_index": session["current_index"],
             "paused_at": session.get("paused_at")},
            {"$set": {"status": "active", "current_index": index, "inflight_attempt_id": None,
                      "inflight_claim_token": None,
                      "attempt_count": 0 if index != session["current_index"] else session["attempt_count"],
                      "pause_reason": None},
             "$push": {"session_events": {"type": "break_ended" if voluntary_owner_break else "session_resumed",
                                          "reason": session.get("pause_reason"), "at": self.clock()}}},
        )
        if updated.modified_count != 1:
            raise HTTPException(409, detail="word_session_transition_conflict")
        return await self.snapshot(session_id, actor)

    async def summary(self, session_id: str, actor: dict):
        session = await self._load(session_id, actor)
        if actor.get('role') not in ('user', 'therapist'):
            raise HTTPException(403, detail='word_session_report_access_denied')
        # SES-005: retiring/editing a plan must not erase access to its history.
        # A former therapist still loses access when the child is reassigned.
        if actor.get('role') == 'therapist':
            child = await self.db.users.find_one({'_id': oid(session['owner_id'])})
            if (not child or child.get('therapist_id') != str(actor['_id'])
                    or not await report_share_allowed(self.db, session['owner_id'], str(actor['_id']))):
                raise HTTPException(403, detail='word_session_access_denied')
        try:
            report = build_session_summary(session)
            plan_words = set(session.get("word_ids") or [])
            report["word_labels"] = {entry.word_id: entry.canonical_tamil
                                     for entry in self.vocabulary.entries if entry.word_id in plan_words}
            return report
        except ValueError as exc:
            raise HTTPException(409, detail=str(exc)) from exc

    async def snapshot(self, session_id: str, actor: dict) -> dict:
        session = await self.sessions.find_one({"_id": session_id})
        if session is None:
            raise HTTPException(status_code=404, detail="word_session_not_found")
        if not self._authorized(session, actor):
            raise HTTPException(status_code=403, detail="word_session_access_denied")
        await self._require_current_plan(session)
        index = session.get("current_index", 0)
        words = session.get("word_ids") or []
        entry = next((item for item in self.vocabulary.entries
                      if isinstance(index, int) and 0 <= index < len(words) and item.word_id == words[index]), None)
        return {"session_id": session_id, "status": session.get("status"),
                "word_id": entry.word_id if entry else None,
                "target_word": entry.canonical_tamil if entry else None,
                "exercise_version": session.get("vocabulary_version"),
                "attempt_count": session.get("attempt_count", 0),
                "total_attempts": session.get("total_attempts", 0),
                "session_limits": session.get("session_limits"), "pause_reason": session.get("pause_reason")}
