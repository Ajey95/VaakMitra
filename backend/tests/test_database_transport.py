"""MOD-008: local Mongo transport must not silently enable TLS."""
import asyncio
from unittest.mock import AsyncMock
from app import database


def test_mod008_concurrent_readiness_performs_one_reconnect(monkeypatch):
    manager = database.Database()
    monkeypatch.setattr(database, 'db_manager', manager)
    count = []
    async def connect():
        count.append(1)
        await asyncio.sleep(0.01)
        manager.client = type('Client', (), {'admin': type('Admin', (), {'command': AsyncMock()})()})()
        manager.db = object()
        manager.connected = True
    monkeypatch.setattr(database, 'connect_to_mongo', connect)
    async def scenario():
        values = await asyncio.gather(database.ensure_database(), database.ensure_database())
        assert values[0] is values[1]
        assert len(count) == 1
    asyncio.run(scenario())


def test_plain_local_mongo_does_not_enable_tls(monkeypatch):
    captured = {}
    class Client:
        admin = type('Admin', (), {'command': AsyncMock()})()
        def __init__(self, uri, **options):
            captured.update(options)
        def __getitem__(self, name):
            return self
        def __getattr__(self, name):
            return self
        create_index = AsyncMock()
        update_one = AsyncMock()
        close = AsyncMock()
    monkeypatch.setattr(database, 'AsyncMongoClient', Client)
    monkeypatch.setattr(database, 'db_manager', database.Database())
    monkeypatch.setattr(database.settings, 'MONGODB_TLS_ALLOW_INVALID_CERTIFICATES', False)
    asyncio.run(database.connect_to_mongo())
    assert 'tlsAllowInvalidCertificates' not in captured
    assert database.db_manager.connected
