"""
Full pipeline integration test — M3.5

Exercises the complete attempt pipeline end-to-end:
  Unity HTTP request → session orchestrator → M1 stub → M2 stub
  → adaptive engine → DB persistence → Unity response

Uses the FastAPI HTTPX test client.
"""

from __future__ import annotations

import base64
import json

import pytest

SAMPLE_EXERCISES = [
    {
        "id": "TA_AMMA_01",
        "target_word": "அம்மா",
        "target_phonemes": ["a", "m", "m", "a:"],
        "syllables": ["அம்", "மா"],
        "difficulty": "easy",
    },
    {
        "id": "TA_APPA_01",
        "target_word": "அப்பா",
        "target_phonemes": ["a", "p", "p", "a:"],
        "syllables": ["அப்", "பா"],
        "difficulty": "easy",
    },
]


@pytest.fixture
def silent_audio_b64():
    return base64.b64encode(bytes(16000 * 2)).decode()


# ---------------------------------------------------------------------------
# Seed helper via therapist plan upload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(api_client):
    """Backend health endpoint must return ok."""
    resp = await api_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "policy_version" in data


@pytest.mark.asyncio
async def test_full_attempt_pipeline_via_api(api_client, seeded_plan, silent_audio_b64):
    """
    Full end-to-end pipeline test via the HTTP API:
    1. Start session
    2. Submit attempt
    3. Verify Unity-facing response structure
    4. End session
    """
    plan_id = seeded_plan

    # 1. Start session
    start_resp = await api_client.post(
        "/api/v1/session/start",
        json={"pseudonym_id": "child-test-uuid-0001", "plan_id": plan_id},
    )
    assert start_resp.status_code == 201, start_resp.text
    session_data = start_resp.json()
    session_id = session_data["session_id"]
    assert session_data["first_exercise_id"] == "TA_AMMA_01"

    # 2. Submit attempt
    attempt_resp = await api_client.post(
        "/api/v1/session/attempt",
        json={
            "session_id": session_id,
            "exercise_id": "TA_AMMA_01",
            "target_word": "அம்மா",
            "audio_b64": silent_audio_b64,
        },
    )
    assert attempt_resp.status_code == 200, attempt_resp.text
    result = attempt_resp.json()

    # 3. Verify Unity-facing response structure (matches §5 contract)
    assert "session_id" in result
    assert "attempt_id" in result
    assert "result" in result
    assert "response_intent" in result
    assert "prompt_audio_id" in result
    assert "avatar_state" in result
    assert "next_exercise_id" in result
    assert "attempts_remaining" in result
    assert "persisted" in result
    assert "sync_eligible" in result
    assert result["session_id"] == session_id

    # Verify no forbidden DATA fields in Unity response (prompt_audio_id is allowed)
    forbidden_data_keys = ["audio_bytes", "audio_data", "pcm", "mfcc", "embedding", "phoneme_prob"]
    for key in forbidden_data_keys:
        assert key not in result, f"Forbidden field '{key}' leaked into Unity response!"
    result_str = json.dumps(result).lower()
    assert "mfcc" not in result_str
    assert "embedding" not in result_str
    assert "phoneme_prob" not in result_str

    # 4. End session
    end_resp = await api_client.post(
        "/api/v1/session/end",
        json={"session_id": session_id},
    )
    assert end_resp.status_code == 200
    end_data = end_resp.json()
    assert end_data["status"] == "completed"


@pytest.mark.asyncio
async def test_cancel_attempt_via_api(api_client, seeded_plan):
    """cancel endpoint must return 200 OK."""
    resp = await api_client.post(
        "/api/v1/session/cancel",
        json={"session_id": "SES-NOOP", "reason": "user_cancelled"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_submit_without_session_returns_400(api_client, silent_audio_b64):
    """Submitting an attempt with an unknown session_id must return 400."""
    resp = await api_client.post(
        "/api/v1/session/attempt",
        json={
            "session_id": "DOES-NOT-EXIST",
            "exercise_id": "TA_AMMA_01",
            "target_word": "அம்மா",
            "audio_b64": silent_audio_b64,
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unity_response_does_not_expose_model_internals(
    api_client, seeded_plan, silent_audio_b64
):
    """
    The Unity-facing response must not expose raw model internals:
    no phoneme probabilities, no embeddings, no raw scores.
    """
    start_resp = await api_client.post(
        "/api/v1/session/start",
        json={"pseudonym_id": "child-test-uuid-0001", "plan_id": seeded_plan},
    )
    session_id = start_resp.json()["session_id"]

    attempt_resp = await api_client.post(
        "/api/v1/session/attempt",
        json={
            "session_id": session_id,
            "exercise_id": "TA_AMMA_01",
            "target_word": "அம்மா",
            "audio_b64": silent_audio_b64,
        },
    )
    result = attempt_resp.json()

    # These fields must NOT appear in Unity response
    forbidden_in_response = {
        "phoneme_probs", "embeddings", "mfcc", "spectrogram",
        "audio_bytes", "audio_data", "waveform", "gop_raw", "confidence_raw",
    }
    for field in forbidden_in_response:
        assert field not in result, (
            f"Model internal field '{field}' leaked into Unity response!"
        )
