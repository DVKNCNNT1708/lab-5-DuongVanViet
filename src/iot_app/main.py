import os
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from typing import Annotated, Dict, List, Literal, Optional, Union

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "ai-vision")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:9000")
MODEL_NAME = os.getenv("MODEL_NAME", "yolo-hospital-monitor")
MODEL_VERSION = os.getenv("MODEL_VERSION", "yolov11n-hospital-2.3.1")


app = FastAPI(
    title="AI Vision Detection API",
    version=SERVICE_VERSION,
    description=(
        "Provider API for Pair 01 - Camera Stream -> AI Vision. "
        "The service accepts image references, stores detection requests, and "
        "returns mock or backend-assisted detection results."
    ),
)


class DetectionStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertHint(str, Enum):
    REVIEW_SECURITY = "REVIEW_SECURITY"
    MONITOR = "MONITOR"
    NONE = "NONE"


class ObjectType(str, Enum):
    PERSON = "PERSON"
    WHEELCHAIR = "WHEELCHAIR"
    STRETCHER = "STRETCHER"
    SMOKE = "SMOKE"
    FIRE_EXTINGUISHER = "FIRE_EXTINGUISHER"
    UNKNOWN = "UNKNOWN"


class ProblemItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    code: str
    message: str


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: List[ProblemItem] = Field(default_factory=list)


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    time: str


class ImageUrlSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceType: Literal["IMAGE_URL"]
    url: str


class ObjectStorageSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceType: Literal["OBJECT_STORAGE_REF"]
    bucket: str = Field(..., min_length=3, max_length=100)
    objectKey: str = Field(..., min_length=3, max_length=300)
    expiresAt: str


ImageSource = Annotated[
    Union[ImageUrlSource, ObjectStorageSource],
    Field(discriminator="sourceType"),
]


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requestId: str = Field(..., pattern=r"^REQ-[A-Z0-9-]+$")
    cameraId: str = Field(..., pattern=r"^CAM-[A-Z0-9-]+$")
    capturedAt: str
    traceId: str = Field(..., pattern=r"^TRACE-[A-Z0-9-]+$")
    zoneId: Optional[str] = Field(default=None, min_length=2, max_length=80)
    motionLevel: Optional[float] = Field(default=None, ge=0, le=1)
    notes: Optional[str] = Field(default=None, min_length=1, max_length=300)
    imageSource: ImageSource


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)


class DetectedObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectType: ObjectType
    label: Optional[str] = Field(default=None, min_length=1, max_length=80)
    confidence: float = Field(..., ge=0, le=1)
    trackId: Optional[str] = Field(default=None, min_length=1, max_length=80)
    boundingBox: BoundingBox


class DetectionSnapshot(BaseModel):
    status: DetectionStatus
    confidence: float = Field(..., ge=0, le=1)
    riskLevel: RiskLevel
    modelVersion: str = Field(..., min_length=3, max_length=100)
    summary: Optional[str] = Field(default=None, min_length=3, max_length=300)
    alertHint: Optional[AlertHint] = None
    completedAt: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    objects: List[DetectedObject] = Field(default_factory=list, min_length=0, max_length=50)


class DetectionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detectionId: str = Field(..., pattern=r"^DET-[0-9]{8}-[0-9]{4}$")
    requestId: str = Field(..., pattern=r"^REQ-[A-Z0-9-]+$")
    traceId: str = Field(..., pattern=r"^TRACE-[A-Z0-9-]+$")
    status: DetectionStatus
    acceptedAt: str
    preliminaryResult: Optional[DetectionSnapshot] = None


class DetectionResult(DetectionSnapshot):
    detectionId: str = Field(..., pattern=r"^DET-[0-9]{8}-[0-9]{4}$")
    requestId: str = Field(..., pattern=r"^REQ-[A-Z0-9-]+$")
    traceId: str = Field(..., pattern=r"^TRACE-[A-Z0-9-]+$")
    processedAt: str


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modelName: str = Field(..., min_length=3, max_length=100)
    modelVersion: str = Field(..., min_length=3, max_length=100)
    supportedObjectTypes: List[ObjectType] = Field(..., min_length=1, max_length=20)
    supportedImageSourceTypes: List[Literal["IMAGE_URL", "OBJECT_STORAGE_REF"]] = Field(
        ..., min_length=1, max_length=5
    )
    maxImageSizeBytes: int = Field(..., ge=1024, le=104857600)
    notes: Optional[str] = Field(default=None, min_length=3, max_length=300)
    lastUpdatedAt: Optional[str] = None


DETECTIONS: Dict[str, DetectionResult] = {}
REQUEST_INDEX: Dict[str, str] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def problem_response(
    *,
    status_code: int,
    title: str,
    detail: Optional[str],
    request: Optional[Request] = None,
    problem_type: str,
    errors: Optional[List[ProblemItem]] = None,
) -> Dict:
    return {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url) if request else None,
        "errors": [item.model_dump() for item in (errors or [])],
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = problem_response(
            status_code=exc.status_code,
            title=HTTPStatus(exc.status_code).phrase,
            detail=str(exc.detail),
            request=request,
            problem_type="https://hospital-campus.local/errors/request-failed",
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", HTTPStatus(exc.status_code).phrase)
    problem.setdefault("type", "https://hospital-campus.local/errors/request-failed")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url))
    problem.setdefault("errors", [])

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
    errors: List[ProblemItem] = []
    for item in exc.errors():
        location = ".".join(str(part) for part in item.get("loc", []))
        errors.append(
            ProblemItem(
                field=location or "body",
                code=str(item.get("type", "VALIDATION_ERROR")).upper(),
                message=item.get("msg", "Request validation error"),
            )
        )

    detail = errors[0].message if errors else "Request validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Unsupported camera registration",
            detail=detail,
            request=request,
            problem_type="https://hospital-campus.local/errors/unprocessable",
            errors=errors,
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=problem_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Authentication required",
                detail="Bearer token is missing or invalid",
                problem_type="https://hospital-campus.local/errors/unauthorized",
            ),
        )


def next_detection_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"DET-{today}-{len(DETECTIONS) + 1:04d}"


def backend_prediction(payload: DetectionRequest) -> Dict:
    default_prediction = {
        "confidence": 0.98,
        "riskLevel": "HIGH",
        "summary": f"Person detected near {payload.zoneId or payload.cameraId}",
        "alertHint": "REVIEW_SECURITY",
        "thumbnailUrl": f"https://media.hospital.local/thumbnails/{payload.requestId}.jpg",
        "objects": [
            {
                "objectType": "PERSON",
                "label": "human",
                "confidence": 0.99,
                "trackId": "TRACK-77",
                "boundingBox": {"x": 0.12, "y": 0.08, "width": 0.41, "height": 0.82},
            }
        ],
    }

    try:
        response = requests.post(
            f"{AI_SERVICE_URL.rstrip('/')}/predict",
            json=payload.model_dump(mode="json"),
            timeout=3,
        )
        if response.ok:
            data = response.json()
            for key in default_prediction:
                data.setdefault(key, default_prediction[key])
            return data
    except requests.RequestException:
        pass

    return default_prediction


@app.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(status="ok", service=SERVICE_NAME, time=now_iso())


@app.post(
    "/vision/detect",
    response_model=DetectionSubmission,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        400: {"model": Problem},
        401: {"model": Problem},
        403: {"model": Problem},
        409: {"model": Problem},
        413: {"model": Problem},
        422: {"model": Problem},
        503: {"model": Problem},
    },
)
def create_detection(
    payload: DetectionRequest,
    request: Request,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
) -> DetectionSubmission:
    if payload.requestId in REQUEST_INDEX:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=problem_response(
                status_code=status.HTTP_409_CONFLICT,
                title="Duplicate request",
                detail=f"requestId {payload.requestId} already exists",
                request=request,
                problem_type="https://hospital-campus.local/errors/conflict",
            ),
        )

    accepted_at = now_iso()
    detection_id = next_detection_id()
    prediction = backend_prediction(payload)
    processed_at = now_iso()

    result = DetectionResult(
        detectionId=detection_id,
        requestId=payload.requestId,
        traceId=payload.traceId,
        status=DetectionStatus.COMPLETED,
        confidence=prediction["confidence"],
        riskLevel=prediction["riskLevel"],
        modelVersion=MODEL_VERSION,
        summary=prediction.get("summary"),
        alertHint=prediction.get("alertHint"),
        processedAt=processed_at,
        completedAt=processed_at,
        thumbnailUrl=prediction.get("thumbnailUrl"),
        objects=[DetectedObject(**item) for item in prediction.get("objects", [])],
    )
    DETECTIONS[detection_id] = result
    REQUEST_INDEX[payload.requestId] = detection_id

    return DetectionSubmission(
        detectionId=detection_id,
        requestId=payload.requestId,
        traceId=payload.traceId,
        status=DetectionStatus.PROCESSING,
        acceptedAt=accepted_at,
        preliminaryResult=None,
    )


@app.get(
    "/vision/detections/{detectionId}",
    response_model=DetectionResult,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": Problem}, 403: {"model": Problem}, 404: {"model": Problem}, 503: {"model": Problem}},
)
def get_detection_by_id(
    request: Request,
    detectionId: str = Path(..., pattern=r"^DET-[0-9]{8}-[0-9]{4}$"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
) -> DetectionResult:
    result = DETECTIONS.get(detectionId)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=problem_response(
                status_code=status.HTTP_404_NOT_FOUND,
                title="Detection not found",
                detail=f"detectionId {detectionId} does not exist",
                request=request,
                problem_type="https://hospital-campus.local/errors/not-found",
            ),
        )
    return result


@app.get(
    "/vision/models/info",
    response_model=ModelInfo,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": Problem}, 403: {"model": Problem}, 503: {"model": Problem}},
)
def get_model_info(
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
) -> ModelInfo:
    return ModelInfo(
        modelName=MODEL_NAME,
        modelVersion=MODEL_VERSION,
        supportedObjectTypes=[
            ObjectType.PERSON,
            ObjectType.WHEELCHAIR,
            ObjectType.STRETCHER,
            ObjectType.SMOKE,
        ],
        supportedImageSourceTypes=["IMAGE_URL", "OBJECT_STORAGE_REF"],
        maxImageSizeBytes=5242880,
        notes="Tuned for indoor hospital corridor and entrance cameras",
        lastUpdatedAt="2026-05-01T00:00:00Z",
    )
