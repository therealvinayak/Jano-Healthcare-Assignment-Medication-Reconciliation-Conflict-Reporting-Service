from pymongo import MongoClient

from app.core.config import get_settings


_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_database():
    settings = get_settings()
    return get_mongo_client()[settings.mongodb_db]
