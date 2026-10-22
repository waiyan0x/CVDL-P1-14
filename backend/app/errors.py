"""Uniform safe errors shared by validation, media and inference boundaries."""
import logging

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(HTTPException):
    def __init__(self, status_code, code, message):
        self.code = code
        super().__init__(status_code, message)


def install_error_handlers(app):
    @app.exception_handler(AppError)
    async def application_error(request, exc):
        return JSONResponse({'error': {'code': exc.code, 'message': exc.detail}}, status_code=exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse({'error': {'code': 'http_error', 'message': str(exc.detail)}}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        issue = exc.errors()[0]
        field = '.'.join(str(part) for part in issue['loc'] if part not in ('body', 'query'))
        return JSONResponse({'error': {'code': 'invalid_options', 'message': f"{field}: {issue['msg']}"}}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        logging.exception('Unhandled request failure', exc_info=exc)
        return JSONResponse({'error': {'code': 'processing_error', 'message': 'Processing failed. Please retry or choose another input.'}}, status_code=500)
