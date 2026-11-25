"""Validated application settings; environment overrides use the EDS_ prefix.

ElevenLabs speech uses its own names (ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID_EN, ELEVENLABS_VOICE_ID_ZH,
ELEVENLABS_MODEL_ID), read from the environment or from an untracked .env.local at the repository root.
"""
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from .schemas.analysis import Backend

ROOT = Path(__file__).resolve().parents[2]

# Setting name -> environment variable for the ElevenLabs text-to-speech integration.
SPEECH_ENV = {'elevenlabs_api_key': 'ELEVENLABS_API_KEY', 'elevenlabs_voice_en': 'ELEVENLABS_VOICE_ID_EN',
              'elevenlabs_voice_zh': 'ELEVENLABS_VOICE_ID_ZH', 'elevenlabs_model': 'ELEVENLABS_MODEL_ID'}


def read_env_file(path):
    """KEY=value lines from a dotenv-style file; blank lines and # comments are skipped."""
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.removeprefix('export ').split('=', 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    root: Path = ROOT
    detector_device: str = 'cpu'
    torchserve_port: int | None = Field(None, ge=1024, le=65535)
    detector_weights: Path | None = None
    trocr_cache: Path | None = None
    easyocr_cache: Path | None = None
    paddle_python: Path | None = None
    paddle_model: Path | None = None
    paddle_pretrained_model: Path | None = None
    detector_image_size: int = Field(640, ge=320, le=1920)
    detector_nms_iou: float = Field(.70, gt=0, le=1)
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
    default_backend: Backend = 'paddleocr'
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_voice_en: str | None = None
    elevenlabs_voice_zh: str | None = None
    # Flash v2.5: lowest latency, and it speaks both English and Mandarin.
    elevenlabs_model: str = 'eleven_flash_v2_5'
    tts_max_chars: int = Field(600, ge=1, le=5000)
    tts_cache_entries: int = Field(256, ge=0, le=10_000)

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
        return self

    @property
    def detector_path(self):
        return self._path(
            self.detector_weights,
            'evaluation/object_detection/01760a841333/runs/v4-reviewed-01/checkpoints/yolo11s-best.pt',
        )

    @property
    def trocr_dir(self):
        return self._path(self.trocr_cache, '.cache/trocr')

    @property
    def easyocr_dir(self):
        return self._path(self.easyocr_cache, '.cache/easyocr')

    @property
    def paddle_python_path(self):
        # PaddlePaddle needs its own Python (3.12); the app's interpreter is newer than Paddle supports.
        return self._path(self.paddle_python, '.cache/paddle-baseline-env/bin/python')

    @property
    def paddle_model_dir(self):
        # Selected model: round 1 fine-tuned en_PP-OCRv5_mobile_rec, Colab run 20261117-031848.
        return self._path(self.paddle_model, 'models/paddleocr-finetuned')

    @property
    def paddle_pretrained_dir(self):
        # Public en_PP-OCRv5_mobile_rec; reads whole-display crops when field crops are unusable.
        return self._path(self.paddle_pretrained_model, 'models/paddleocr-pretrained')

    @property
    def upload_dir(self):
        return self.root / '.runtime/uploads'

    def limits(self):
        return {'image_upload_bytes': self.max_image_bytes, 'video_upload_bytes': self.max_video_bytes,
                'max_video_duration_seconds': self.max_video_duration_seconds,
                'default_interval_ms': self.default_interval_ms, 'min_interval_ms': self.min_interval_ms}

    @property
    def voices(self):
        """Configured ElevenLabs voice per spoken language ('en', 'zh')."""
        return {language: voice for language, voice in
                (('en', self.elevenlabs_voice_en), ('zh', self.elevenlabs_voice_zh)) if voice}

    @classmethod
    def from_env(cls, env_file=ROOT / '.env.local'):
        # The process environment wins over .env.local.
        environ = {**read_env_file(env_file), **os.environ}
        values = {name: environ[f'EDS_{name.upper()}'] for name in cls.model_fields
                  if f'EDS_{name.upper()}' in environ}
        values.update({name: environ[key] for name, key in SPEECH_ENV.items() if environ.get(key)})
        return cls(**values)
