"""Runtime readiness and available sample images."""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix='/api', tags=['system'])


@router.get('/health')
def health(request: Request):
    runtime, settings = request.app.state.runtime, request.app.state.settings
    backends = runtime.backends
    default = settings.default_backend if settings.default_backend in backends else next(iter(backends), None)
    return {'ready': runtime.ready, 'error': runtime.error, 'backends': backends,
            'default_backend': default, 'limits': settings.limits(),
            'confidence_note': 'OCR scores are engine-specific heuristics, not calibrated accuracy.'}


@router.get('/samples')
def samples(request: Request):
    return request.app.state.samples.list()


@router.get('/samples/{sample_id}/image')
def sample_image(sample_id: int, request: Request):
    return FileResponse(request.app.state.samples.path(sample_id))
