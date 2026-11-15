from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routers import story_voice
from app.services.story_voice import (
    STORY_VOICE_LINES,
    StoryVoiceService,
    StoryVoiceUnavailable,
)
from app.utils.jwt_handler import get_current_user


@pytest.mark.asyncio
async def test_story_voice_service_uses_fixed_tamil_line_and_caches_audio():
    calls = []

    async def transport(text, api_key, voice_id):
        calls.append((text, api_key, voice_id))
        return b"mp3-audio"

    service = StoryVoiceService(
        api_key="server-secret",
        voice_id="cute-kavi",
        transport=transport,
    )

    first = await service.get_audio("page_1")
    second = await service.get_audio("page_1")

    assert first == second == b"mp3-audio"
    assert calls == [(STORY_VOICE_LINES["page_1"], "server-secret", "cute-kavi")]


@pytest.mark.asyncio
async def test_story_voice_service_rejects_arbitrary_text_and_disabled_provider():
    service = StoryVoiceService(api_key="", voice_id="")

    with pytest.raises(KeyError):
        await service.get_audio("அந்தக் குழந்தை சொன்ன உரை")
    with pytest.raises(StoryVoiceUnavailable):
        await service.get_audio("page_1")


def test_story_voice_route_is_authenticated_allow_listed_and_returns_mp3(monkeypatch):
    class FakeVoiceService:
        async def get_audio(self, line_id):
            assert line_id == "page_1"
            return b"fixed-line-audio"

    monkeypatch.setattr(story_voice, "story_voice_service", FakeVoiceService())
    app = FastAPI()
    app.include_router(story_voice.router)
    app.dependency_overrides[get_current_user] = lambda: {"_id": "parent-1"}

    with TestClient(app) as client:
        ok = client.get("/api/story-voice/page_1")
        rejected = client.get("/api/story-voice/arbitrary-child-text")

    assert ok.status_code == 200
    assert ok.content == b"fixed-line-audio"
    assert ok.headers["content-type"] == "audio/mpeg"
    assert ok.headers["cache-control"] == "private, max-age=3600"
    assert rejected.status_code == 404


def test_story_voice_route_reports_disabled_provider_without_leaking_config(monkeypatch):
    class DisabledVoiceService:
        async def get_audio(self, _line_id):
            raise StoryVoiceUnavailable("secret provider configuration detail")

    monkeypatch.setattr(story_voice, "story_voice_service", DisabledVoiceService())
    app = FastAPI()
    app.include_router(story_voice.router)
    app.dependency_overrides[get_current_user] = lambda: {"_id": "parent-1"}

    response = TestClient(app).get("/api/story-voice/page_1")

    assert response.status_code == 503
    assert response.json() == {"detail": "story_voice_unavailable"}

