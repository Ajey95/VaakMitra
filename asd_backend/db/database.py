"""
Async SQLAlchemy engine / session factory.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from asd_backend.db.encryption import get_db_url
from asd_backend.db.models import Base

_engine = create_async_engine(
    get_db_url(),
    echo=False,          # set True for SQL query logging in dev
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_session_factory() -> async_sessionmaker:
    """Return the current AsyncSessionLocal (respects test engine swaps)."""
    return AsyncSessionLocal


async def init_db() -> None:
    """Create all tables on first run (idempotent)."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
