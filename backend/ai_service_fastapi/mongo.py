from __future__ import annotations

from functools import lru_cache

import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "curamind")


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)


def get_ai_result(image_id: str):
    doc = _client()[MONGO_DB].ai_results.find_one({"image_id": image_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return doc.get("result")


def check_mongo_connection() -> bool:
    try:
        _client().admin.command("ping")
        return True
    except PyMongoError:
        return False
