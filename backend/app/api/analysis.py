"""Image and same-frame comparison endpoints with admission before decoding."""
import logging
import time

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from ..errors import AppError
from ..media.images import decode_image
from ..schemas.analysis import AnalysisResponse, ComparisonResponse
from .submissions import Submission, parse_submission

router = APIRouter(prefix='/api', tags=['analysis'])


async def analyse_submission(request, submission, comparison=False):
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    # Acquire on the event loop before bytes are read/decoded or work is dispatched.
    with runtime.admit(None if comparison else submission.options.backend) as pipeline:
        started = time.perf_counter()
        if submission.file is not None:
            data = await submission.file.read(settings.max_image_bytes + 1)
        else:
            data = request.app.state.samples.path(submission.sample_id).read_bytes()
        try:
            def process():
                image = decode_image(data, settings, trusted_sample=submission.sample_id is not None)
                method = pipeline.compare if comparison else pipeline.analyse
                return method(image, submission.options, started)
            return await run_in_threadpool(process)
        except AppError:
            raise
        except Exception as exc:
            logging.exception('Image analysis failed')
            raise AppError(500, 'processing_error', 'Image processing failed. Retry or choose another OCR engine.') from exc


@router.post('/analysis', response_model=AnalysisResponse)
async def analysis(request: Request, submission: Submission = Depends(parse_submission)):
    return await analyse_submission(request, submission)


@router.post('/comparisons', response_model=ComparisonResponse)
async def comparisons(request: Request, submission: Submission = Depends(parse_submission)):
    return await analyse_submission(request, submission, comparison=True)
