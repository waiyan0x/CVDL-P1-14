"""Image and same-frame comparison endpoints with admission before decoding."""
import logging
import time

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from ..errors import AppError
from ..media.images import decode_image
from ..schemas.analysis import AnalysisResponse, ComparisonResponse
from .submissions import parse_submission


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


async def submission_response(request, comparison=False):
    async with request.form() as form:
        result = await analyse_submission(request, parse_submission(form), comparison)
    model = ComparisonResponse if comparison else AnalysisResponse
    return JSONResponse(model.model_validate(result).model_dump(mode='json'))


async def analysis(request):
    return await submission_response(request)


async def comparisons(request):
    return await submission_response(request, comparison=True)
