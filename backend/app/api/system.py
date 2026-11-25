"""Runtime readiness and available sample images."""

from starlette.responses import FileResponse, JSONResponse

from .submissions import SAMPLE_ID


def health_status(app):
    runtime, settings = app.state.runtime, app.state.settings
    backends = runtime.backends
    default = settings.default_backend if settings.default_backend in backends else next(iter(backends), None)
    detector_runtime = getattr(runtime, 'detector_runtime', None)
    detector_ready = detector_runtime != 'torchserve' or runtime.pipeline.detector.is_ready()
    error = runtime.error if detector_ready else 'TorchServe detector is unavailable.'
    return {
        'ready': runtime.ready and detector_ready, 'error': error, 'backends': backends,
        'default_backend': default, 'limits': settings.limits(),
        'detector_runtime': detector_runtime,
        'confidence_note': 'OCR scores are engine-specific heuristics, not calibrated accuracy.',
    }


def health(request):
    return JSONResponse(health_status(request.app))


def readyz(request):
    state = health_status(request.app)
    ready = (state['ready'] and state['detector_runtime'] == 'torchserve'
             and set(state['backends']) == {'easyocr', 'paddleocr', 'trocr'})
    return JSONResponse(state, status_code=200 if ready else 503)


def samples(request):
    return JSONResponse(request.app.state.samples.list())


def sample_image(request):
    sample_id = SAMPLE_ID.validate_python(request.path_params['sample_id'])
    return FileResponse(request.app.state.samples.path(sample_id))
