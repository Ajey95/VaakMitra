"""SES-001: additive indexes; duplicate legacy sessions require explicit repair."""


async def migrate_word_sessions(db):
    # Index build failure leaves DB readiness false; no historical sessions are deleted.
    await db.word_sessions.create_index(
        [("owner_id", 1)], unique=True,
        partialFilterExpression={"status": {"$in": ["active", "paused"]}, "owner_id": {"$type": "string"}},
        name="one_open_word_session_per_owner_v2",
    )
    await db.word_sessions.create_index([("owner_id", 1), ("restart_after", -1)])
    await db.schema_migrations.update_one({"_id": "word-sessions-v2"},
        {"$setOnInsert": {"requirements": ["SES-001", "SES-005"], "version": 2}}, upsert=True)
