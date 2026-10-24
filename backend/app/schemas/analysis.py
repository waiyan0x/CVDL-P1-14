"""Explicit frame, confidence and timing contracts exposed in OpenAPI."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

Backend = Literal['easyocr', 'tesseract', 'trocr']
AnalysisStatus = Literal['no_eds', 'unreadable', 'partial', 'unknown_match', 'matched']


class FrameOptions(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    backend: Backend = 'easyocr'
    detection: float = Field(.3, ge=.05, le=.95)
    ocr_threshold: float = Field(.25, ge=0, le=1)
    similarity: float = Field(.7, ge=0, le=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100)
    frame_id: int = Field(0, ge=0)
    source: Literal['image', 'sample', 'camera', 'video'] = 'image'
    source_timestamp_ms: float = Field(0, ge=0)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('captured_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('captured_at must include a timezone.')
        return value

    def frame(self):
        return {key: value for key, value in self.model_dump(mode='json').items()
                if key in ('session_id', 'frame_id', 'source', 'source_timestamp_ms', 'captured_at')}


class VideoFrameOptions(FrameOptions):
    source: Literal['video'] = 'video'
    timestamp_ms: float = Field(0, ge=0)


class Detection(BaseModel):
    id: str
    display_id: str
    label: Literal['bus_number', 'destination', 'eds']
    box: tuple[int, int, int, int]
    confidence: float | None = Field(None, ge=0, le=1)
    source: Literal['model', 'field_union'] = 'model'


class Screen(Detection):
    crop: str


class FieldResult(Detection):
    raw: str
    ocr_confidence: float | None = Field(None, ge=0, le=1)
    ocr_confidence_method: str
    crop: str


class ReferenceMatch(BaseModel):
    status: Literal['matched', 'service_only', 'unmatched']
    service: str | None
    endpoint: str | None
    similarity: float | None
    reason: str
    routes: list[dict[str, str]]


class DisplayResult(BaseModel):
    display_id: str
    status: AnalysisStatus
    message: str
    screen: Screen | None
    fields: dict[str, FieldResult]
    match: ReferenceMatch


class Timings(BaseModel):
    preprocessing_ms: float
    detection_ms: float
    ocr_ms: float
    matching_ms: float
    total_ms: float


class ProcessedFrame(BaseModel):
    session_id: str
    frame_id: int
    source: Literal['image', 'sample', 'camera', 'video']
    source_timestamp_ms: float
    captured_at: datetime
    processed_at: datetime


class AnalysisResponse(BaseModel):
    frame: ProcessedFrame
    status: AnalysisStatus
    message: str
    backend: Backend
    image: str
    width: int
    height: int
    detections: list[Detection]
    results: list[DisplayResult]
    timings: Timings
    processing_fps: float


class ComparisonEntry(BaseModel):
    backend: Backend
    status: Literal['success', 'unavailable', 'error']
    result: AnalysisResponse | None
    error: str | None


class ComparisonResponse(BaseModel):
    frame: ProcessedFrame
    image: str
    width: int
    height: int
    detections: list[Detection]
    comparisons: list[ComparisonEntry]
