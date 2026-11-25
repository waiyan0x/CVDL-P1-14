"""Real server-side video validation and sampled-frame decoding; no job queue."""

import logging
import mimetypes
import time

from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, JSONResponse, Response

from ..errors import AppError
from ..schemas.analysis import AnalysisResponse, VideoFrameOptions
from .submissions import required_file


async def upload_video(request):
    async with request.form() as form:
        file = required_file(form)
        media = await run_in_threadpool(request.app.state.videos.add, file.file, file.filename)
    return JSONResponse(media)


def video_content(request):
    entry = request.app.state.videos.get(request.path_params['video_id'])
    return FileResponse(entry['path'], media_type=mimetypes.guess_type(entry['name'])[0] or 'application/octet-stream')


async def video_frame(request):
    video_id = request.path_params['video_id']
    options = VideoFrameOptions.model_validate_json(await request.body())
    with request.app.state.runtime.admit(options.backend) as pipeline:
        started = time.perf_counter()

        def process():
            image, actual_ms = request.app.state.videos.frame(video_id, options.timestamp_ms)
            actual_options = options.model_copy(update={'source_timestamp_ms': actual_ms})
            return pipeline.analyse(image, actual_options, started)

        try:
            result = await run_in_threadpool(process)
        except AppError:
            raise
        except Exception as exc:
            logging.exception('Video frame processing failed')
            raise AppError(500, 'processing_error', 'Video frame processing failed. Retry or choose another OCR engine.') from exc
    return JSONResponse(AnalysisResponse.model_validate(result).model_dump(mode='json'))


def delete_video(request):
    request.app.state.videos.delete(request.path_params['video_id'])
    return Response(status_code=204)
