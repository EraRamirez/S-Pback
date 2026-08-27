import httpx
import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db import mongo as mongo_module
from app.main import app


@pytest.fixture(autouse=True)
def mock_db():
    mongo_module._db = AsyncMongoMockClient()["saas_pymes"]


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
