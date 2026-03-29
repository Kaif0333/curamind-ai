from __future__ import annotations

from datetime import datetime, timezone
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


@lru_cache(maxsize=1)
def ensure_indexes() -> bool:
    try:
        db = get_db()
        db.ai_results.create_index("image_id", unique=True)
        db.image_metadata.create_index("image_id", unique=True)
        db.processing_logs.create_index([("image_id", 1), ("_id", 1)])
        return True
    except PyMongoError:
        logger.exception("Failed to ensure MongoDB indexes for AI engine collections")
        return False


def store_ai_result(image_id: str, result: dict) -> str:
    ensure_indexes()
    doc = {
        "image_id": image_id,
        "result": result,
        "updated_at": datetime.now(timezone.utc),
    }
    write_result = get_db().ai_results.replace_one({"image_id": image_id}, doc, upsert=True)
    return str(write_result.upserted_id or image_id)


def store_image_metadata(image_id: str, metadata: dict) -> str:
    ensure_indexes()
    doc = {
        "image_id": image_id,
        "metadata": metadata,
        "updated_at": datetime.now(timezone.utc),
    }
    write_result = get_db().image_metadata.replace_one(
        {"image_id": image_id},
        doc,
        upsert=True,
    )
    return str(write_result.upserted_id or image_id)


def store_processing_log(
    image_id: str,
    stage: str,
    status: str,
    details: dict | None = None,
) -> str:
    ensure_indexes()
    doc = {
        "image_id": image_id,
        "stage": stage,
        "status": status,
        "details": details or {},
        "created_at": datetime.now(timezone.utc),
    }
    inserted = get_db().processing_logs.insert_one(doc)
    return str(inserted.inserted_id)


def get_ai_result_by_image(image_id: str) -> dict | None:
    try:
        return get_db().ai_results.find_one({"image_id": image_id}, sort=[("updated_at", -1)])
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


def get_processing_logs_by_image(image_id: str) -> list[dict]:
    try:
        logs = list(get_db().processing_logs.find({"image_id": image_id}).sort("_id", 1))
    except PyMongoError:
        logger.exception("Failed to fetch processing logs for image %s", image_id)
        return []

    for log in logs:
        log["_id"] = str(log["_id"])
    return logs
