"""FastAPI application assembly. Run uvicorn backend.app.main:app."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .api import analysis, system, videos
from .api.body_limits import BodyLimitMiddleware
from .config import Settings
from .errors import install_error_handlers
from .media.videos import VideoStore
from .services.runtime import Runtime
from .services.samples import SampleRegistry


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

    app = FastAPI(title='EDS Reader', version='1.0.0', lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware, settings=settings)
    app.state.settings = settings
    app.state.samples = SampleRegistry(settings.root)
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(analysis.router)
    app.include_router(videos.router)
    from .api.evaluation import router as evaluation_router
    app.include_router(evaluation_router)
    app.mount('/assets', StaticFiles(directory=settings.root / 'frontend/assets', check_dir=False), name='assets')

    def page(name):
        return FileResponse(settings.root / 'frontend/pages' / f'{name}.html')

    @app.get('/', include_in_schema=False)
    @app.get('/detect', include_in_schema=False)
    def detect_page():
        return page('detect')

    @app.get('/live', include_in_schema=False)
    def live_page():
        return page('live')

    @app.get('/evaluation', include_in_schema=False)
    def evaluation_page():
        return page('evaluation')

    @app.get('/models', include_in_schema=False)
    def models_page():
        return page('models')

    return app


app = create_app()
