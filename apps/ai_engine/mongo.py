from __future__ import annotations

from functools import lru_cache
import logging

from django.conf import settings
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    return MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=1000)


def get_db():
    return _client()[settings.MONGO_DB_NAME]


def store_ai_result(image_id: str, result: dict) -> str:
    doc = {"image_id": image_id, "result": result}
    inserted = get_db().ai_results.insert_one(doc)
    return str(inserted.inserted_id)


def store_image_metadata(image_id: str, metadata: dict) -> str:
    doc = {"image_id": image_id, "metadata": metadata}
    inserted = get_db().image_metadata.insert_one(doc)
    return str(inserted.inserted_id)


def get_ai_result_by_image(image_id: str) -> dict | None:
    try:
        return get_db().ai_results.find_one({"image_id": image_id})
    except PyMongoError:
        logger.exception("Failed to fetch AI result for image %s", image_id)
        return None


def get_ai_result_by_id(result_id: str) -> dict | None:
    try:
        oid = ObjectId(result_id)
    except Exception:
        return None
    try:
        return get_db().ai_results.find_one({"_id": oid})
    except PyMongoError:
        logger.exception("Failed to fetch AI result by id %s", result_id)
        return None
