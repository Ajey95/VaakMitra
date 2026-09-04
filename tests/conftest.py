"""
Shared pytest fixtures for ASD-Edge-ST backend tests.
"""

from __future__ import annotations

import os
# Set before any asd_backend imports so lifespan startup is skipped in tests
os.environ.setdefault("ASD_TESTING", "1")

import asd_backend.db.database as _db_module

import asyncio
import base64
import os as _os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.db.models import Base
from asd_backend.db.repositories import (
    ChildProfileRepository,
    ExercisePlanRepository,
    SessionRepository,
)


# ---------------------------------------------------------------------------
# Async event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# In-memory test database
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Fresh in-memory SQLite for every test function."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine) -> AsyncSession:
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _use_test_engine(engine):
    """Redirect the module-level DB engine to the given test engine and create tables."""
    _db_module._engine = engine
    _db_module.AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# Default test policy
# ---------------------------------------------------------------------------

@pytest.fixture
def default_policy() -> TherapistPolicy:
    return TherapistPolicy.default()


# ---------------------------------------------------------------------------
# Sample exercise plan
# ---------------------------------------------------------------------------

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


@pytest_asyncio.fixture
async def seeded_plan(test_db) -> str:
    """Create a child profile + exercise plan in the test DB, return plan_id."""
    child_repo = ChildProfileRepository(test_db)
    await child_repo.create("child-test-uuid-0001", consent_version="1.0")

    plan_repo = ExercisePlanRepository(test_db)
    plan = await plan_repo.create(
        therapist_ref="test-therapist",
        policy_version="0.0.1-dev",
        plan_version="1.0.0",
        exercises=SAMPLE_EXERCISES,
    )
    await test_db.commit()
    return plan.plan_id


# ---------------------------------------------------------------------------
# Tiny valid audio stub (16 kHz mono PCM, 1 second of silence)
# ---------------------------------------------------------------------------

@pytest.fixture
def silent_audio_b64() -> str:
    """Base64 of 1 second of 16 kHz mono 16-bit silence."""
    pcm_silence = bytes(16000 * 2)  # 1s × 16000 samples × 2 bytes
    return base64.b64encode(pcm_silence).decode()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def api_client(test_engine):
    """Async HTTPX client against the FastAPI app with test DB injected."""
    # Redirect DB to test engine and create all tables
    await _use_test_engine(test_engine)

    # Initialise orchestrator with default policy (bypasses lifespan)
    from asd_backend.session.api import init_orchestrator
    init_orchestrator(policy=TherapistPolicy.default())

    # Import app AFTER engine is patched
    from asd_backend.main import app

    # Use lifespan=False transport so startup/shutdown hooks are skipped
    # (they would try to create DB tables on the wrong engine)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as client:
        yield client
