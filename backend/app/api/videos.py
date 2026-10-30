"""Real server-side video validation and sampled-frame decoding; no job queue."""
import logging
import mimetypes
import time

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool

from ..errors import AppError
from ..schemas.analysis import AnalysisResponse, VideoFrameOptions

router = APIRouter(prefix='/api/videos', tags=['videos'])


@router.post('')
async def upload_video(request: Request, file: UploadFile = File(...)):
    return await run_in_threadpool(request.app.state.videos.add, file.file, file.filename)


@router.get('/{video_id}/content')
def video_content(video_id: str, request: Request):
    entry = request.app.state.videos.get(video_id)
    return FileResponse(entry['path'], media_type=mimetypes.guess_type(entry['name'])[0] or 'application/octet-stream')


@router.post('/{video_id}/frames', response_model=AnalysisResponse)
async def video_frame(video_id: str, options: VideoFrameOptions, request: Request):
    with request.app.state.runtime.admit(options.backend) as pipeline:
        started = time.perf_counter()
        def process():
            image, actual_ms = request.app.state.videos.frame(video_id, options.timestamp_ms)
            actual_options = options.model_copy(update={'source_timestamp_ms': actual_ms})
            return pipeline.analyse(image, actual_options, started)
        try:
            return await run_in_threadpool(process)
        except AppError:
            raise
        except Exception as exc:
            logging.exception('Video frame processing failed')
            raise AppError(500, 'processing_error', 'Video frame processing failed. Retry or choose another OCR engine.') from exc


@router.delete('/{video_id}', status_code=204)
def delete_video(video_id: str, request: Request):
    request.app.state.videos.delete(video_id)
    return Response(status_code=204)
