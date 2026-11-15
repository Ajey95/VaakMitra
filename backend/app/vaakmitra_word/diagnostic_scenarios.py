"""SES-001..006: explicit synthetic model scenarios against a real isolated MongoDB."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException

from .contracts import AssessmentResult, Decision, ReasonCode
from .migrations import migrate_word_sessions
from .session_limits import SessionLimits
from .session_state import WordSessionStore


async def run_scenarios(client, vocabulary):
    name = "vaakmitra_lab_scenario_" + uuid4().hex
    db = client[name]
    results = []
    moment = [datetime.now(timezone.utc)]
    child, therapist, plan = ObjectId(), ObjectId(), ObjectId()
    owner = {"_id": child, "role": "user"}
    adult = {"_id": therapist, "role": "therapist"}
    words = [entry for entry in vocabulary.entries if entry.kind == "word"][:2]
    limits = SessionLimits(max_retries=1).model_dump()
    base = {"owner_id": str(child), "therapist_id": str(therapist), "plan_id": str(plan),
            "word_ids": [item.word_id for item in words], "vocabulary_version": vocabulary.version,
            "session_limits": limits, "status": "active", "current_index": 0, "attempt_count": 0,
            "total_attempts": 0, "completed_attempt_ids": [], "attempts": [],
            "inflight_attempt_id": None, "created_at": moment[0]}
    store = WordSessionStore(db, vocabulary, clock=lambda: moment[0])

    def record(label, condition):
        results.append({"name": label, "passed": bool(condition)})

    async def claim(attempt):
        return await store.claim("SES-SYNTHETIC", attempt, words[0].word_id, words[0].canonical_tamil,
                                 vocabulary.version, owner)

    def decision(attempt, outcome):
        return AssessmentResult(session_id="SES-SYNTHETIC", attempt_id=attempt, word_id=words[0].word_id,
            target_word=words[0].canonical_tamil, decision=outcome,
            reason_code=ReasonCode.CALIBRATED_TARGET_MATCH if outcome == Decision.PASS else ReasonCode.CALIBRATED_WORD_MISMATCH,
            word_match_probability=0.9 if outcome == Decision.PASS else 0.1)

    try:
        await migrate_word_sessions(db)
        await db.users.insert_one({"_id": child, "role": "user", "therapist_id": str(therapist), "synthetic_fixture": True})
        await db.treatment_plans.insert_one({"_id": plan, "child_id": str(child), "therapist_id": str(therapist),
            "word_ids": base["word_ids"], "vocabulary_version": vocabulary.version, "session_limits": limits, "status": "active"})
        await db.word_sessions.insert_one({"_id": "SES-SYNTHETIC", **base})
        try:
            await store.snapshot("SES-SYNTHETIC", {"_id": ObjectId(), "role": "user"})
            record("Unassigned account denied", False)
        except HTTPException as exc:
            record("Unassigned account denied", exc.status_code == 403)
        first = await claim("A1")
        try:
            await claim("A1")
            record("Concurrent attempt rejected", False)
        except HTTPException as exc:
            record("Concurrent attempt rejected", exc.status_code == 409)
        await store.complete(first, decision("A1", Decision.RETRY))
        second = await claim("A2")
        await store.complete(second, decision("A2", Decision.RETRY))
        state = await store.snapshot("SES-SYNTHETIC", owner)
        record("Retry limit pauses session", state["status"] == "paused" and state["total_attempts"] == 2)
        try:
            await store.resume("SES-SYNTHETIC", owner)
            record("Child cannot authorize adult continuation", False)
        except HTTPException as exc:
            record("Child cannot authorize adult continuation", exc.status_code == 403)
        try:
            await store.resume("SES-SYNTHETIC", adult, next_word_id=words[1].word_id)
            record("Break interval enforced", False)
        except HTTPException as exc:
            record("Break interval enforced", exc.status_code == 409)
        moment[0] += timedelta(seconds=31)
        resumed = await store.resume("SES-SYNTHETIC", adult, next_word_id=words[1].word_id)
        record("Adult switches within assigned plan", resumed["word_id"] == words[1].word_id and resumed["total_attempts"] == 2)
        await store.pause("SES-SYNTHETIC", owner)
        await store.resume("SES-SYNTHETIC", adult, next_word_id=words[0].word_id)
        pending = await claim("A3")
        await store.stop("SES-SYNTHETIC", owner)
        cancelled = await store.complete(pending, decision("A3", Decision.PASS))
        record("Stop suppresses a late PASS", cancelled.decision == Decision.UNSCORABLE and cancelled.reason_code == ReasonCode.CANCELLED)
        # RPT-007: synthetic lifecycle checks use the owner; no fabricated report-sharing grant.
        summary = await store.summary("SES-SYNTHETIC", owner)
        record("Summary reflects persisted completed attempts", summary["completed_attempts"] == 2 and summary["decisions"]["RETRY"] == 2)
        doc = await db.word_sessions.find_one({"_id": "SES-SYNTHETIC"})
        blocked = {"audio", "transcript", "embeddings", "evidence", "observed_candidates", "word_match_probability"}
        record("Stored attempt summaries exclude voice evidence", all(not (set(item) & blocked) for item in doc["attempts"]))
        # SES-003/005: exercise the atomic reservation against real MongoDB, not
        # only the in-memory race fixture used by the deterministic unit test.
        await db.word_sessions.insert_one({"_id": "SES-REPLAY", **base})
        old_claim = await store.claim("SES-REPLAY", "P1", words[0].word_id, words[0].canonical_tamil,
                                      vocabulary.version, owner)
        await store.pause("SES-REPLAY", owner)
        await store.resume("SES-REPLAY", adult)
        replay_denied = False
        try:
            await store.claim("SES-REPLAY", "P1", words[0].word_id, words[0].canonical_tamil,
                              vocabulary.version, owner)
        except HTTPException as exc:
            replay_denied = exc.status_code == 409
        late = await store.complete(old_claim, AssessmentResult(session_id="SES-REPLAY", attempt_id="P1",
            word_id=words[0].word_id, target_word=words[0].canonical_tamil,
            decision=Decision.PASS, reason_code=ReasonCode.CALIBRATED_TARGET_MATCH,
            word_match_probability=0.9))
        replay_doc = await db.word_sessions.find_one({"_id": "SES-REPLAY"})
        record("Pause-resume rejects replay and stale PASS", replay_denied and late.decision == Decision.UNSCORABLE
               and replay_doc["current_index"] == 0 and not replay_doc["attempts"])
        await store.stop("SES-REPLAY", owner)
        # A separate synthetic session checks crash recovery and elapsed-time exhaustion.
        await db.word_sessions.insert_one({"_id": "SES-LEASE", **base})
        pending = await store.claim("SES-LEASE", "L1", words[0].word_id, words[0].canonical_tamil, vocabulary.version, owner)
        moment[0] += timedelta(seconds=20)
        try:
            await store.claim("SES-LEASE", "L2", words[0].word_id, words[0].canonical_tamil, vocabulary.version, owner)
            record("Abandoned inference lease recovers to pause", False)
        except HTTPException as exc:
            record("Abandoned inference lease recovers to pause", exc.detail == "word_attempt_lease_expired")
        moment[0] += timedelta(seconds=700)
        try:
            await store.resume("SES-LEASE", adult)
            record("Session duration cannot be reset by resume", False)
        except HTTPException as exc:
            record("Session duration cannot be reset by resume", exc.detail == "word_session_limit_reached")
        return {"scope": "synthetic_model_real_database", "checks": results, "passed": all(item["passed"] for item in results)}
    finally:
        # The name is generated here, never supplied by the request or config.
        if name.startswith("vaakmitra_lab_scenario_") and len(name) == len("vaakmitra_lab_scenario_") + 32:
            await client.drop_database(name)
