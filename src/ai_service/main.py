"""Simple AI service mock for Lab 05."""

import os
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_NAME = "ai-service"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "v0.1.0-team-iot")

app = FastAPI(
    title="FIT4110 Lab 05 - AI Service",
    version=SERVICE_VERSION,
    description="Mock AI service used in the Docker Compose stack.",
)


class Prediction(BaseModel):
    objects: List[str]
    confidence: List[float]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/predict", response_model=Prediction)
def predict() -> Prediction:
    return Prediction(objects=["person", "bicycle"], confidence=[0.98, 0.85])
