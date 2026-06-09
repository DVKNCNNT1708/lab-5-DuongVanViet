import os
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from typing import Dict, List, Optional

import psycopg
import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "v0.1.0-team-iot")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")
DATABASE_URL = os.getenv("DATABASE_URL")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")

app = FastAPI(
    title="FIT4110 Lab 05 - IoT Ingestion Service",
    version=SERVICE_VERSION,
    description=(
        "IoT Ingestion API for Lab 05. The service can run locally with "
        "in-memory storage, or inside Docker Compose with PostgreSQL and an AI service."
    ),
)


class SensorMetric(str, Enum):
    temperature = "temperature"
    humidity = "humidity"
    motion = "motion"
    smoke = "smoke"


class SensorUnit(str, Enum):
    celsius = "celsius"
    percent = "percent"
    boolean = "boolean"
    ppm = "ppm"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class DependencyHealth(BaseModel):
    database: str
    ai_service: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    dependencies: DependencyHealth


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., min_length=3, examples=["ESP32-LAB-A01"])
    metric: SensorMetric = Field(..., examples=["temperature"])
    value: float = Field(
        ...,
        ge=-40,
        le=80,
        description="Boundary range used in Lab 03 and Lab 04: -40 to 80.",
        examples=[31.5],
    )
    unit: Optional[SensorUnit] = Field(default=None, examples=["celsius"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class SensorReading(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    value: float
    unit: Optional[SensorUnit] = None
    timestamp: str
    created_at: str


class SensorReadingCreated(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    accepted: bool
    created_at: str


READINGS: List[Dict] = []


def status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=status_phrase(exc.status_code),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status_phrase(exc.status_code))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_reading_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    if DATABASE_URL:
        with db_connection() as conn:
            count = conn.execute("SELECT COUNT(*) AS total FROM readings").fetchone()["total"]
        return f"R-{today}-{count + 1:04d}"
    return f"R-{today}-{len(READINGS) + 1:04d}"


def db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_database() -> None:
    if not DATABASE_URL:
        return

    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                reading_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                unit TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def check_database() -> str:
    if not DATABASE_URL:
        return "disabled"
    try:
        with db_connection() as conn:
            conn.execute("SELECT 1")
        return "ok"
    except Exception:
        return "error"


def check_ai_service() -> str:
    if not AI_SERVICE_URL:
        return "disabled"
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=3)
        return "ok" if response.status_code == 200 else "error"
    except requests.RequestException:
        return "error"


def call_ai_predict() -> None:
    if not AI_SERVICE_URL:
        return
    try:
        response = requests.post(f"{AI_SERVICE_URL}/predict", timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=build_problem(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                title="AI service unavailable",
                detail=f"Could not call AI service: {exc}",
                problem_type="https://smart-campus.local/problems/ai-unavailable",
            ),
        ) from exc


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database_status = check_database()
    ai_status = check_ai_service()
    overall = "ok" if database_status != "error" and ai_status != "error" else "degraded"
    return HealthResponse(
        status=overall,
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        dependencies=DependencyHealth(database=database_status, ai_service=ai_status),
    )


@app.head("/health")
def health_head() -> Response:
    return Response(status_code=status.HTTP_200_OK)


@app.post(
    "/readings",
    response_model=SensorReadingCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        503: {"model": ProblemDetails},
    },
)
def create_reading(payload: SensorReadingCreate, response: Response) -> SensorReadingCreated:
    call_ai_predict()

    if payload.metric == SensorMetric.temperature and payload.value >= 70:
        response.headers["X-Warning"] = "high-temperature"

    reading_id = next_reading_id()
    created_at = now_iso()
    item = {
        "reading_id": reading_id,
        "device_id": payload.device_id,
        "metric": payload.metric.value,
        "value": payload.value,
        "unit": payload.unit.value if payload.unit else None,
        "timestamp": payload.timestamp,
        "created_at": created_at,
    }

    if DATABASE_URL:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO readings (
                    reading_id, device_id, metric, value, unit, timestamp, created_at
                )
                VALUES (
                    %(reading_id)s, %(device_id)s, %(metric)s, %(value)s,
                    %(unit)s, %(timestamp)s, %(created_at)s
                )
                """,
                item,
            )
            conn.commit()
    else:
        READINGS.append(item)

    return SensorReadingCreated(
        reading_id=reading_id,
        device_id=payload.device_id,
        metric=payload.metric,
        accepted=True,
        created_at=created_at,
    )


@app.get("/readings/latest", dependencies=[Depends(verify_bearer_token)])
def latest_readings(
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> Dict[str, List[Dict]]:
    if DATABASE_URL:
        params = {"limit": limit}
        where_clause = ""
        if device_id:
            where_clause = "WHERE device_id = %(device_id)s"
            params["device_id"] = device_id
        with db_connection() as conn:
            items = conn.execute(
                f"""
                SELECT reading_id, device_id, metric, value, unit, timestamp, created_at
                FROM readings
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %(limit)s
                """,
                params,
            ).fetchall()
        return {"items": list(reversed(items))}

    items = READINGS
    if device_id:
        items = [item for item in items if item["device_id"] == device_id]
    return {"items": items[-limit:]}


@app.get("/readings/{reading_id}", dependencies=[Depends(verify_bearer_token)])
def get_reading(reading_id: str) -> Dict:
    if DATABASE_URL:
        with db_connection() as conn:
            item = conn.execute(
                """
                SELECT reading_id, device_id, metric, value, unit, timestamp, created_at
                FROM readings
                WHERE reading_id = %(reading_id)s
                """,
                {"reading_id": reading_id},
            ).fetchone()
        if item:
            return item
    else:
        for item in READINGS:
            if item["reading_id"] == reading_id:
                return item

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Reading {reading_id} does not exist",
            instance=f"/readings/{reading_id}",
            problem_type="https://smart-campus.local/problems/not-found",
        ),
    )
