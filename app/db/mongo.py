# app/db/mongo.py
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

_client: Optional[AsyncIOMotorClient] = None

def init_client() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)

def get_client() -> AsyncIOMotorClient:
    if _client is None:
        # not created yet — but prefer calling init_client in lifespan
        init_client()
    return _client

def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None

def get_master_db():
    client = get_client()
    return client[settings.MASTER_DB]

def get_org_collection(collection_name: str):
    db = get_master_db()
    return db[collection_name]
