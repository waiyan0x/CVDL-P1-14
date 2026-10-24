"""Multipart request boundary shared by analysis and comparison."""
from dataclasses import dataclass

from fastapi import File, Form, UploadFile
from pydantic import ValidationError

from ..errors import AppError
from ..schemas.analysis import FrameOptions


@dataclass
class Submission:
    options: FrameOptions
    file: UploadFile | None
    sample_id: int | None


def parse_submission(file: UploadFile | None = File(None), sample_id: int | None = Form(None),
                     backend: str = Form('easyocr'), detection: float = Form(.3),
                     ocr_threshold: float = Form(.25), similarity: float = Form(.7),
                     session_id: str | None = Form(None), frame_id: int = Form(0), source: str = Form('image'),
                     source_timestamp_ms: float = Form(0), captured_at: str | None = Form(None)):
    if (file is None) == (sample_id is None):
        raise AppError(400, 'input_required', 'Provide either an image file or one sample ID.')
    values = dict(backend=backend, detection=detection, ocr_threshold=ocr_threshold, similarity=similarity,
                  frame_id=frame_id, source=source, source_timestamp_ms=source_timestamp_ms)
    if session_id is not None:
        values['session_id'] = session_id
    if captured_at is not None:
        values['captured_at'] = captured_at
    try:
        return Submission(FrameOptions(**values), file, sample_id)
    except ValidationError as exc:
        issue = exc.errors()[0]
        raise AppError(422, 'invalid_options', f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}") from exc
