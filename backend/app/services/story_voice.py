"""Optional external voice synthesis for a finite set of authored Tamil lines."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx

from ..config import settings


STORY_VOICE_LINES = {
    "page_1": "கவி ஆற்றங்கரையில் நிற்கிறான். பாதையைத் திறக்க அ என்று சொல்லலாமா?",
    "page_2": "மின்மினிப் பூச்சிகள் வழி காட்ட வேண்டும். ஈ என்று நீளமாகச் சொல்லுங்கள்.",
    "page_3": "கவி தன் அம்மாவை அழைக்க வேண்டும். அம்மா என்று சொல்லுங்கள்.",
    "page_4": "பாலம் அருகே வந்துவிட்டது. கவி வா என்று அழையுங்கள்.",
    "page_5": "கவி பாலத்தைக் கடக்கத் தயாராக இருக்கிறான். கவி பாலத்தைக் கடக்கலாம் என்று சொல்லுங்கள்.",
    "wonderful": "அருமை! மிக அழகாகச் சொன்னீர்கள்!",
    "almost": "நன்றாக முயன்றீர்கள்! இன்னொரு முறை மெதுவாகச் சொல்லலாமா?",
    "try_together": "கவியுடன் சேர்ந்து மெதுவாகச் சொல்லலாம்.",
    "model_unavailable": "நான் கேட்கிறேன். படத்தைப் பார்த்து நாமே சேர்ந்து சொல்லலாம்.",
    "complete": "அருமை! கவி பாலத்தைக் கடந்துவிட்டான்!",
}

VoiceTransport = Callable[[str, str, str], Awaitable[bytes]]


class StoryVoiceUnavailable(RuntimeError):
    """Raised when the optional authored-line voice provider cannot respond."""


class StoryVoiceService:
    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        transport: VoiceTransport | None = None,
    ) -> None:
        self._api_key = settings.ELEVENLABS_API_KEY if api_key is None else api_key
        self._voice_id = settings.ELEVENLABS_STORY_VOICE_ID if voice_id is None else voice_id
        self._transport = transport or self._elevenlabs_transport
        self._cache: dict[str, bytes] = {}

    async def get_audio(self, line_id: str) -> bytes:
        if line_id not in STORY_VOICE_LINES:
            raise KeyError(line_id)
        if line_id in self._cache:
            return self._cache[line_id]
        if not self._api_key or not self._voice_id:
            raise StoryVoiceUnavailable("Story voice provider is not configured")
        try:
            audio = await self._transport(
                STORY_VOICE_LINES[line_id], self._api_key, self._voice_id
            )
        except StoryVoiceUnavailable:
            raise
        except Exception as exc:
            raise StoryVoiceUnavailable("Story voice provider failed") from exc
        if not audio:
            raise StoryVoiceUnavailable("Story voice provider returned no audio")
        self._cache[line_id] = audio
        return audio

    @staticmethod
    async def _elevenlabs_transport(text: str, api_key: str, voice_id: str) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": api_key, "Accept": "audio/mpeg"}
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.62, "similarity_boost": 0.72},
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as exc:
            raise StoryVoiceUnavailable("Story voice provider failed") from exc


story_voice_service = StoryVoiceService()
