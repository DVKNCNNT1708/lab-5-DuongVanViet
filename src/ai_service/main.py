"""
Simple inference backend mock for the AI Vision provider API.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

SERVICE_NAME = os.getenv("AI_BACKEND_SERVICE_NAME", "ai-model-backend")
SERVICE_VERSION = os.getenv("MODEL_VERSION", "yolov11n-hospital-2.3.1")

app = FastAPI(
    title="AI Vision Backend Mock",
    version=SERVICE_VERSION,
    description="Mock backend used by the provider API to simulate model inference.",
)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    requestId: str
    cameraId: str


class PredictResponse(BaseModel):
    confidence: float
    riskLevel: str
    summary: str
    alertHint: str
    thumbnailUrl: str
    objects: List[Dict[str, Any]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "time": now_iso()}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    thumbnail = f"https://media.hospital.local/thumbnails/{payload.requestId}.jpg"
    return PredictResponse(
        confidence=0.98,
        riskLevel="HIGH",
        summary=f"Person detected near camera {payload.cameraId}",
        alertHint="REVIEW_SECURITY",
        thumbnailUrl=thumbnail,
        objects=[
            {
                "objectType": "PERSON",
                "label": "human",
                "confidence": 0.99,
                "trackId": "TRACK-77",
                "boundingBox": {"x": 0.12, "y": 0.08, "width": 0.41, "height": 0.82},
            }
        ],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
