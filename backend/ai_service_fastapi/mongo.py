from __future__ import annotations

from functools import lru_cache
import logging

import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "curamind")
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)


@lru_cache(maxsize=1)
def ensure_indexes() -> bool:
    try:
        db = _client()[MONGO_DB]
        db.ai_results.create_index("image_id", unique=True)
        db.image_metadata.create_index("image_id", unique=True)
        db.processing_logs.create_index([("image_id", 1), ("_id", 1)])
        return True
    except PyMongoError:
        logger.exception("Failed to ensure MongoDB indexes for FastAPI service")
        return False


def get_ai_result(image_id: str):
    ensure_indexes()
    doc = _client()[MONGO_DB].ai_results.find_one({"image_id": image_id}, sort=[("updated_at", -1)])
    if not doc:
        return None
    doc.pop("_id", None)
    return doc.get("result")


def check_mongo_connection() -> bool:
    try:
        _client().admin.command("ping")
        ensure_indexes()
        return True
    except PyMongoError:
        return False
