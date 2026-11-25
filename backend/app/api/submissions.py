"""Multipart request boundary shared by analysis and comparison."""

from dataclasses import dataclass

from pydantic import TypeAdapter
from starlette.datastructures import UploadFile

from ..errors import AppError
from ..schemas.analysis import FrameOptions

SAMPLE_ID = TypeAdapter(int)


@dataclass
class Submission:
    options: FrameOptions
    file: UploadFile | None
    sample_id: int | None


def required_file(form):
    file = form.get('file')
    if not isinstance(file, UploadFile):
        raise AppError(422, 'invalid_options', 'file: Provide an uploaded file.')
    return file


def parse_submission(form):
    file = required_file(form) if form.get('file') not in (None, '') else None
    raw_sample_id = form.get('sample_id')
    sample_id = SAMPLE_ID.validate_python(raw_sample_id) if raw_sample_id not in (None, '') else None
    if (file is None) == (sample_id is None):
        raise AppError(400, 'input_required', 'Provide either an image file or one sample ID.')
    values = {key: form[key] for key in FrameOptions.model_fields if key in form and form[key] != ''}
    return Submission(FrameOptions.model_validate(values), file, sample_id)
