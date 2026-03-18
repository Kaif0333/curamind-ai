from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .model import predict_image
from .mongo import get_ai_result

app = FastAPI(title="CuraMind AI Inference Service")


@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
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
