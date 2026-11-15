"""Database connection and collection lifecycle.

PyMongo's native asyncio driver is used instead of Motor.  Motor is now in
deprecated maintenance mode, while ``AsyncMongoClient`` is the supported
asyncio path for new deployments.
"""
import asyncio
from typing import Any, Optional

from pymongo import AsyncMongoClient
from fastapi import HTTPException, status
from .config import settings


class Database:
    """MongoDB database manager."""
    
    client: Optional[AsyncMongoClient] = None
    db: Any = None
    connected: bool = False

    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self.reconnect_lock = asyncio.Lock()


db_manager = Database()


async def connect_to_mongo():
    """Connect to MongoDB Atlas and build the indexes used by the API."""
    try:
        db_manager.client = AsyncMongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=3000,
            # PyMongo enables TLS even when this option is explicitly False.
            # Omit it to preserve the URI transport (Atlas SRV still enables TLS).
            **({"tlsAllowInvalidCertificates": True} if settings.MONGODB_TLS_ALLOW_INVALID_CERTIFICATES else {}),
        )
        db_manager.db = db_manager.client[settings.DB_NAME]

        # Ping to verify connection (will raise if Atlas IP not whitelisted)
        await db_manager.client.admin.command("ping")

        # Create indexes
        await db_manager.db.users.create_index("email", unique=True)
        await db_manager.db.evaluations.create_index("user_id")
        await db_manager.db.progress.create_index([("user_id", 1), ("lesson_id", 1)])
        await db_manager.db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        await db_manager.db.feedback.create_index([("user_id", 1), ("created_at", -1)])
        await db_manager.db.appointments.create_index([("therapist_id", 1), ("scheduled_at", 1)])
        await db_manager.db.appointments.create_index([("user_id", 1), ("scheduled_at", 1)])
        await db_manager.db.appointments.create_index("open_checkup_key", unique=True,
                                                      partialFilterExpression={"open_checkup_key": {"$exists": True}})
        await db_manager.db.appointments.create_index("active_slot_key", unique=True,
                                                      partialFilterExpression={"active_slot_key": {"$exists": True}})
        await db_manager.db.announcements.create_index([("published", 1), ("created_at", -1)])
        await db_manager.db.calendar_events.create_index([("user_id", 1), ("start", 1)])
        await db_manager.db.settings.create_index("user_id", unique=True)
        await db_manager.db.wallets.create_index("user_id", unique=True)
        await db_manager.db.wallet_transactions.create_index([("user_id", 1), ("created_at", -1)])
        await db_manager.db.inventory.create_index([("user_id", 1), ("item_slug", 1)], unique=True)
        await db_manager.db.games.create_index("slug", unique=True)
        await db_manager.db.game_scores.create_index([("game_slug", 1), ("score", -1)])
        await db_manager.db.game_scores.create_index([("user_id", 1), ("created_at", -1)])
        await db_manager.db.quizzes.create_index("slug", unique=True)
        await db_manager.db.quiz_attempts.create_index([("user_id", 1), ("created_at", -1)])
        await db_manager.db.videos.create_index("slug", unique=True)
        await db_manager.db.video_progress.create_index([("user_id", 1), ("video_slug", 1)], unique=True)
        await db_manager.db.shop_items.create_index("slug", unique=True)
        await db_manager.db.friendships.create_index([("a", 1), ("b", 1)])
        await db_manager.db.audit_logs.create_index([("created_at", -1)])
        await db_manager.db.audit_logs.create_index("action")
        await db_manager.db.reviewer_credentials.create_index([("therapist_id", 1), ("scope", 1), ("created_at", -1)])
        await db_manager.db.consent_receipts.create_index([("child_id", 1), ("created_at", -1)])
        await db_manager.db.consent_decisions.create_index("receipt_id", unique=True)
        await db_manager.db.consent_withdrawals.create_index("receipt_id", unique=True)
        await db_manager.db.report_share_grants.create_index([("child_id", 1), ("created_at", -1)])
        await db_manager.db.review_batches.create_index([("kind", 1), ("created_at", -1)])
        await db_manager.db.review_decisions.create_index([("batch_id", 1), ("item_id", 1)], unique=True)
        await db_manager.db.password_resets.create_index("email")
        await db_manager.db.saved_reports.create_index("user_id")
        await db_manager.db.interactive_sessions.create_index([("user_id", 1), ("created_at", -1)])
        await db_manager.db.word_sessions.create_index([("owner_id", 1), ("created_at", -1)])
        from .vaakmitra_word.migrations import migrate_word_sessions
        await migrate_word_sessions(db_manager.db)

        db_manager.connected = True
        print("[OK] Connected to MongoDB")

    except asyncio.CancelledError:
        await close_mongo_connection()
        raise
    except Exception as e:
        if db_manager.client is not None:
            await db_manager.client.close()
        db_manager.connected = False
        db_manager.db = None
        print(f"[WARN] MongoDB connection failed: {type(e).__name__}")
        if settings.APP_ENV in {"production", "prod"}:
            print("[WARN] API is live but readiness remains unavailable until MongoDB is reachable.")
        else:
            print("[INFO] Local development can continue without MongoDB; DB routes return an error.")


async def close_mongo_connection():
    """Close MongoDB connection."""
    if db_manager.client:
        await db_manager.client.close()
        db_manager.connected = False
        db_manager.client = None
        db_manager.db = None
        print("[INFO] Closed MongoDB connection")


async def ensure_database() -> Any:
    """MOD-008: readiness returns within its budget, including reconnects."""
    try:
        return await asyncio.wait_for(_ensure_database_once(), settings.DATABASE_TIMEOUT_SECONDS)
    except (TimeoutError, asyncio.TimeoutError):
        raise HTTPException(status_code=503, detail="database_timeout") from None


async def _ensure_database_once() -> Any:
    """Return a live database handle, reconnecting stale Atlas connections.

    A process can remain alive while an idle MongoDB connection has been
    dropped by the network or Atlas.  Checking only ``connected`` is not
    enough, so every state-changing request gets a cheap ping first.
    """
    async with db_manager.reconnect_lock:
        if db_manager.db is not None and db_manager.connected:
            try:
                await db_manager.client.admin.command("ping")
                return db_manager.db
            except Exception:
                db_manager.connected = False
                await close_mongo_connection()

        await connect_to_mongo()
        if db_manager.connected:
            return db_manager.db

    return get_database()


def get_database() -> Any:
    """Get the verified database or return a clear service-unavailable error."""
    if db_manager.db is None or not db_manager.connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Configure MongoDB and try again.",
        )
    return db_manager.db
