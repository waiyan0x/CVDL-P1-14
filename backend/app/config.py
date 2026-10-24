"""Validated application settings; environment overrides use the EDS_ prefix."""
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    root: Path = ROOT
    detector_device: str = 'cpu'
    detector_weights: Path | None = None
    trocr_cache: Path | None = None
    easyocr_cache: Path | None = None
    detector_image_size: int = Field(640, ge=320, le=1920)
    torch_threads: int = Field(4, ge=1, le=32)
    max_image_bytes: int = Field(16 * 1024 * 1024, ge=1024)
    max_image_pixels: int = Field(40_000_000, ge=1)
    preview_max_side: int = Field(1920, ge=320, le=4096)
    max_video_bytes: int = Field(256 * 1024 * 1024, ge=1024)
    max_video_duration_seconds: float = Field(600, gt=0)
    video_ttl_seconds: float = Field(3600, gt=0)
    max_video_uploads: int = Field(5, ge=1, le=100)
    default_interval_ms: int = Field(500, ge=100)
    min_interval_ms: int = Field(100, ge=50)
    default_backend: str = 'easyocr'

    @field_validator('root')
    @classmethod
    def absolute_root(cls, value):
        return value.expanduser().resolve()

    def _path(self, override, default):
        path = override or self.root / default
        path = path.expanduser()
        return path if path.is_absolute() else self.root / path

    @model_validator(mode='after')
    def validate_defaults(self):
        if self.default_interval_ms < self.min_interval_ms:
            raise ValueError('Default sampling interval must be at least the minimum interval.')
        if self.default_backend not in ('easyocr', 'tesseract', 'trocr'):
            raise ValueError('Default backend must be easyocr, tesseract or trocr.')
        return self

    @property
    def detector_path(self):
        return self._path(self.detector_weights, 'models/yolo-v6-finetuned/best_v6.pt')

    @property
    def trocr_dir(self):
        return self._path(self.trocr_cache, '.cache/trocr')

    @property
    def easyocr_dir(self):
        return self._path(self.easyocr_cache, '.cache/easyocr')

    @property
    def upload_dir(self):
        return self.root / '.runtime/uploads'

    def limits(self):
        return {'image_upload_bytes': self.max_image_bytes, 'video_upload_bytes': self.max_video_bytes,
                'max_video_duration_seconds': self.max_video_duration_seconds,
                'default_interval_ms': self.default_interval_ms, 'min_interval_ms': self.min_interval_ms}

    @classmethod
    def from_env(cls):
        values = {name: os.environ[f'EDS_{name.upper()}'] for name in cls.model_fields
                  if f'EDS_{name.upper()}' in os.environ}
        return cls(**values)
