from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import io
import struct
from time import sleep
import wave

from fastapi import FastAPI, APIRouter, UploadFile, File
from fastapi.testclient import TestClient

from app.routers import evaluation
from app.utils.jwt_handler import get_current_user
from app.vaakmitra_word.contracts import AssessmentResult, ModelReadiness, ReasonCode
from app.vaakmitra_word.assessment import AssessmentContext
from app.vaakmitra_word.policy import TherapistConstraints
from app.vaakmitra_word.router import (
    get_assessment_service,
    get_readiness_registry,
    get_word_session_store,
    router as word_router,
)
from app.vaakmitra_word.session_state import SessionClaim
from app.vaakmitra_word.upload_limit import WordUploadLimitMiddleware
from app.config import settings


@dataclass
class FakeService:
    contexts: list = field(default_factory=list)

    def assess(self, audio_bytes, context):
        self.contexts.append(context)
        return AssessmentResult.unscorable(
            ReasonCode.MODEL_UNAVAILABLE,
            session_id=context.session_id,
            attempt_id=context.attempt_id,
            word_id=context.word_id,
            target_word=context.target_word,
        )


class UnreadyRegistry:
    def scoring_readiness(self):
        return ModelReadiness(ready=False, reasons=["model_unavailable"])


class FakeWordSessionStore:
    """Literal assigned-session fixture; production authorization is tested separately."""
    async def claim(self, session_id, attempt_id, word_id, target, version, _actor):
        if session_id not in {"SES-registry", "SES-timeout"}:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="word_session_not_found")
        assert version == "ta-words-v1.1.0"
        context = AssessmentContext(
            session_id=session_id, attempt_id=attempt_id, word_id=word_id,
            target_word=target, attempt_count=0,
            therapist_constraints=TherapistConstraints(
                allowed_actions=("repeat", "break", "safe_end"), next_exercise_id=""),
        )
        return SessionClaim(assessment=context, current_index=0, word_count=1)

    async def complete(self, _claim, result):
        return result


def pcm_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00" * 16000)
    return buffer.getvalue()


def compressed_wav() -> bytes:
    # AU-001: A-law format 6 is RIFF/WAVE but not supported by our PCM decoder.
    fmt = struct.pack("<HHIIHH", 6, 1, 16000, 16000, 1, 8)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", 4) + b"\x00" * 4
    return b"RIFF" + struct.pack("<I", len(chunks) + 4) + b"WAVE" + chunks


def client(service: FakeService | None = None) -> tuple[TestClient, FakeService]:
    app = FastAPI()
    app.add_middleware(WordUploadLimitMiddleware)
    app.include_router(word_router)
    app.include_router(evaluation.router)
    fake = service or FakeService()
    app.dependency_overrides[get_assessment_service] = lambda: fake
    app.dependency_overrides[get_readiness_registry] = lambda: UnreadyRegistry()
    app.dependency_overrides[get_word_session_store] = lambda: FakeWordSessionStore()
    app.dependency_overrides[get_current_user] = lambda: {"_id": "P-1"}
    return TestClient(app), fake


def test_prv002_large_bounded_upload_does_not_spool_voice_to_disk():
    app = FastAPI()
    app.add_middleware(WordUploadLimitMiddleware)
    probe = APIRouter(route_class=word_router.route_class)
    @probe.post('/api/v1/word-assessments')
    async def inspect(audio: UploadFile = File(...)):
        return {'spooled_to_disk': audio.file._rolled, 'bytes': len(await audio.read())}
    app.include_router(probe)
    response = TestClient(app).post('/api/v1/word-assessments',
        files={'audio': ('adult.wav', b'x' * (1024 * 1024 + 1), 'audio/wav')})
    assert response.status_code == 200
    assert response.json() == {'spooled_to_disk': False, 'bytes': 1048577}


def test_canonical_target_must_match_server_owned_word() -> None:
    api, service = client()

    response = api.post(
        "/api/v1/word-assessments",
        data={
            "session_id": "SES-1",
            "attempt_id": "ATT-1",
            "word_id": "TA_00021",
            "target_word": "தவறு",
            "exercise_version": "ta-core-1.0.0",
        },
        files={"audio": ("attempt.wav", pcm_wav(), "audio/wav")},
    )

    assert response.status_code == 422
    assert service.contexts == []


def test_au001_webm_is_rejected_before_scoring() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        data={
            "session_id": "SES-1", "attempt_id": "ATT-1", "word_id": "TA_00021",
            "target_word": "அம்மா", "exercise_version": "ta-core-1.0.0",
        },
        files={"audio": ("sample.webm", b"\x1aE\xdf\xa3", "audio/webm")},
    )
    assert response.status_code == 415
    assert service.contexts == []


def test_au003_wav_larger_than_eight_mib_is_rejected() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        data={
            "session_id": "SES-1", "attempt_id": "ATT-1", "word_id": "TA_00021",
            "target_word": "அம்மா", "exercise_version": "ta-core-1.0.0",
        },
        files={"audio": ("sample.wav", b"RIFF" + b"X" * (8 * 1024 * 1024), "audio/wav")},
    )
    assert response.status_code == 413
    assert service.contexts == []


def test_au003_rejects_oversized_multipart_before_field_validation() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        files={"audio": ("sample.wav", b"X" * (8 * 1024 * 1024), "audio/wav")},
    )
    assert response.status_code == 413
    assert service.contexts == []


def test_au003_rejects_chunked_upload_before_parser_without_content_length() -> None:
    invoked = False
    responses = []
    chunks = iter([
        {"type": "http.request", "body": b"a" * (5 * 1024 * 1024), "more_body": True},
        {"type": "http.request", "body": b"b" * (4 * 1024 * 1024), "more_body": False},
    ])

    async def inner(_scope, _receive, _send):
        nonlocal invoked
        invoked = True

    async def receive():
        return next(chunks)

    async def send(message):
        responses.append(message)

    scope = {"type": "http", "method": "POST", "path": "/api/v1/word-assessments", "headers": []}
    asyncio.run(WordUploadLimitMiddleware(inner)(scope, receive, send))
    assert not invoked
    assert responses[0]["status"] == 413


def test_au001_octet_stream_without_wav_header_is_rejected() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        data={
            "session_id": "SES-1", "attempt_id": "ATT-1", "word_id": "TA_00021",
            "target_word": "அம்மா", "exercise_version": "ta-core-1.0.0",
        },
        files={"audio": ("attempt.bin", b"not a WAV stream", "application/octet-stream")},
    )
    assert response.status_code == 415
    assert service.contexts == []


def test_au001_malformed_riff_wave_is_rejected_before_scoring() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        data={"session_id": "SES-1", "attempt_id": "ATT-1", "word_id": "TA_00021",
              "target_word": "அம்மா", "exercise_version": "ta-core-1.0.0"},
        files={"audio": ("attempt.wav", b"RIFF\x04\x00\x00\x00WAVE", "audio/wav")},
    )
    assert response.status_code == 415
    assert service.contexts == []


def test_au001_compressed_riff_wave_is_rejected_before_scoring() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        data={"session_id": "SES-1", "attempt_id": "ATT-1", "word_id": "TA_00021",
              "target_word": "அம்மா", "exercise_version": "ta-core-1.0.0"},
        files={"audio": ("attempt.wav", compressed_wav(), "audio/wav")},
    )
    assert response.status_code == 415
    assert service.contexts == []


def test_ses001_legacy_endpoint_cannot_bypass_plan_session() -> None:
    api, service = client()

    response = api.post(
        "/api/evaluate/speech",
        data={
            "target_phoneme": "amma",
            "lesson_id": "5",
            "browser_transcript": "a transcript that must be ignored",
        },
        files={"audio": ("attempt.wav", pcm_wav(), "audio/wav")},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "word_session_required_use_canonical_endpoint"
    assert service.contexts == []


def test_scoring_health_is_503_when_artifacts_are_missing() -> None:
    api, _ = client()

    response = api.get("/health/scoring")

    assert response.status_code == 503
    assert response.json()["detail"]["reasons"] == ["model_unavailable"]


def test_dec058_vocabulary_endpoint_exposes_104_intended_words() -> None:
    """DEC-016: the application catalog must not remain capped at six constants."""
    api, _ = client()

    response = api.get("/api/v1/vocabulary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["vocabulary_version"] == "ta-words-v1.1.0"
    assert len(payload["entries"]) == 104
    assert payload["entries"][0]["word_id"] == "TA_WORD_0001"
    assert payload["entries"][0]["canonical_tamil"] == "அம்மா"
    assert all(item["kind"] == "word" for item in payload["entries"])
    assert all(item["available_for_scoring"] is False for item in payload["entries"])


def test_new_registry_word_is_server_owned_even_before_activation() -> None:
    """Target text must come from the registry, while readiness still fails closed."""
    api, service = client()

    response = api.post(
        "/api/v1/word-assessments",
        data={
            "session_id": "SES-registry",
            "attempt_id": "ATT-registry",
            "word_id": "TA_WORD_0011",
            "target_word": "தண்ணீர்",
            "exercise_version": "ta-words-v1.1.0",
        },
        files={"audio": ("attempt.wav", pcm_wav(), "audio/wav")},
    )

    assert response.status_code == 200
    assert service.contexts[0].word_id == "TA_WORD_0011"
    assert service.contexts[0].target_word == "தண்ணீர்"


def test_section13_canonical_assessment_rejects_an_unowned_session_before_scoring() -> None:
    api, service = client()
    response = api.post(
        "/api/v1/word-assessments",
        data={"session_id": "SES-arbitrary", "attempt_id": "ATT-1", "word_id": "TA_WORD_0001",
              "target_word": "அம்மா", "exercise_version": "ta-words-v1.1.0"},
        files={"audio": ("attempt.wav", pcm_wav(), "audio/wav")},
    )
    assert response.status_code == 404
    assert service.contexts == []


def test_face_and_unsafe_story_routes_are_not_registered() -> None:
    paths = {route.path for route in evaluation.router.routes}

    assert "/api/evaluate/ws/face/{session_id}" not in paths
    assert "/api/evaluate/tamil-story" not in paths


def test_inference_timeout_returns_scoreless_unscorable(monkeypatch) -> None:
    class SlowService(FakeService):
        def assess(self, audio_bytes, context):
            sleep(0.05)
            return super().assess(audio_bytes, context)

    api, _ = client(SlowService())
    monkeypatch.setattr(settings, "VAAKMITRA_INFERENCE_TIMEOUT_SECONDS", 0.01)

    response = api.post(
        "/api/v1/word-assessments",
        data={
            "session_id": "SES-timeout",
            "attempt_id": "ATT-timeout",
            "word_id": "TA_WORD_0001",
            "target_word": "அம்மா",
            "exercise_version": "ta-words-v1.1.0",
        },
        files={"audio": ("attempt.wav", pcm_wav(), "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "UNSCORABLE"
    assert response.json()["word_match_probability"] is None
    assert response.json()["reason_code"] == "MODEL_TIMEOUT"
