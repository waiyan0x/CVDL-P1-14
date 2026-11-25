"""Assemble the EDS Reader HTTP gateway. Run uvicorn backend.app.main:app."""

from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, HTMLResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .api import analysis, evaluation, speech, system, videos
from .api.body_limits import BodyLimitMiddleware
from .config import Settings
from .errors import install_error_handlers
from .media.videos import VideoStore
from .services.runtime import Runtime
from .services.samples import SampleRegistry
from .services.speech import SpeechSynthesizer


def schema(request):
    return FileResponse(Path(__file__).with_name('openapi.json'), media_type='application/json')


def api_docs(request):
    return HTMLResponse('''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EDS Reader API</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.31.0/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.31.0/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({ url: "/openapi.json", dom_id: "#swagger-ui" });</script>
</body>
</html>
''')


def create_app(settings=None, runtime_factory=Runtime):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        app.state.runtime = runtime_factory(settings)
        await run_in_threadpool(app.state.runtime.start)
        app.state.pipeline = app.state.runtime.pipeline
        app.state.videos = VideoStore(settings)
        try:
            yield
        finally:
            app.state.videos.close()

    def page(name):
        def serve(request):
            return FileResponse(settings.root / 'frontend/pages' / f'{name}.html')

        return serve

    routes = [
        *(Route(path, page(name)) for path, name in (
            ('/', 'home'), ('/detect', 'detect'), ('/live', 'live'),
            ('/evaluation', 'evaluation'), ('/models', 'models'),
        )),
        Route('/docs', api_docs),
        Route('/openapi.json', schema),
        Route('/api/health', system.health),
        Route('/readyz', system.readyz),
        Route('/api/samples', system.samples),
        Route('/api/samples/{sample_id}/image', system.sample_image),
        Route('/api/speech/status', speech.speech_status),
        Route('/api/speech/tts', speech.text_to_speech, methods=['POST']),
        Route('/api/analysis', analysis.analysis, methods=['POST']),
        Route('/api/comparisons', analysis.comparisons, methods=['POST']),
        Route('/api/videos', videos.upload_video, methods=['POST']),
        Route('/api/videos/{video_id}/content', videos.video_content),
        Route('/api/videos/{video_id}/frames', videos.video_frame, methods=['POST']),
        Route('/api/videos/{video_id}', videos.delete_video, methods=['DELETE']),
        *evaluation.routes,
        Mount('/assets', StaticFiles(directory=settings.root / 'frontend/assets', check_dir=False), name='assets'),
    ]
    app = Starlette(routes=routes, lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware, settings=settings)
    app.state.settings = settings
    app.state.samples = SampleRegistry(settings.root)
    app.state.speech = SpeechSynthesizer(settings)
    install_error_handlers(app)
    return app


app = create_app()
