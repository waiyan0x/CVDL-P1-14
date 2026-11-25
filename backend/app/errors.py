"""Uniform safe errors shared by validation, media and inference boundaries."""

import logging

from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


class AppError(HTTPException):
    def __init__(self, status_code, code, message):
        self.code = code
        super().__init__(status_code, message)


async def application_error(request, exc):
    return JSONResponse({'error': {'code': exc.code, 'message': exc.detail}}, status_code=exc.status_code)


async def http_error(request, exc):
    return JSONResponse(
        {'error': {'code': 'http_error', 'message': str(exc.detail)}},
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def validation_error(request, exc):
    issue = exc.errors()[0]
    field = '.'.join(map(str, issue['loc']))
    detail = f"{field}: {issue['msg']}" if field else issue['msg']
    return JSONResponse({'error': {'code': 'invalid_options', 'message': detail}}, status_code=422)


async def unexpected_error(request, exc):
    logging.exception('Unhandled request failure', exc_info=exc)
    return JSONResponse({'error': {'code': 'processing_error', 'message': 'Processing failed. Please retry or choose another input.'}}, status_code=500)


def install_error_handlers(app):
    app.add_exception_handler(AppError, application_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(ValidationError, validation_error)
    app.add_exception_handler(Exception, unexpected_error)
