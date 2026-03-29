from __future__ import annotations

import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .model import get_model_metadata, predict_image, warmup_model
from .mongo import check_mongo_connection, get_ai_result

app = FastAPI(title="CuraMind AI Inference Service")
MAX_UPLOAD_MB = int(os.getenv("AI_MAX_UPLOAD_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
SUPPORTED_CONTENT_TYPES = {
    "application/dicom",
    "application/octet-stream",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "curamind-ai-inference"}


@app.get("/ready")
async def ready():
    try:
        model_metadata = warmup_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Model warmup failed") from exc

    mongo_connected = check_mongo_connection()
    if not mongo_connected:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "service": "curamind-ai-inference",
                "mongo_connected": mongo_connected,
                **model_metadata,
            },
        )

    return {
        "status": "ready",
        "service": "curamind-ai-inference",
        "mongo_connected": mongo_connected,
        **model_metadata,
    }


@app.get("/model-info")
async def model_info():
    return get_model_metadata()


@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type and file.content_type.lower() not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Limit is {MAX_UPLOAD_MB} MB.",
        )
    try:
        result = predict_image(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(result)


@app.get("/ai-result")
async def ai_result(image_id: str):
    result = get_ai_result(image_id)
    if not result:
        raise HTTPException(status_code=404, detail="AI result not found")
    return result
