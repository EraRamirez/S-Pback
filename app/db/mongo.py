from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_uri)
_db: AsyncIOMotorDatabase = _client[settings.mongodb_db]


def get_db() -> AsyncIOMotorDatabase:
    return _db
