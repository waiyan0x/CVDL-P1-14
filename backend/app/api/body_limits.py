"""Bound multipart bodies before the framework spools uploads to disk."""
from fastapi.responses import JSONResponse

from ..errors import AppError


class BodyLimitMiddleware:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] != 'http' or scope.get('method') != 'POST' or not path.startswith('/api/'):
            return await self.app(scope, receive, send)
        limit = self.settings.max_video_bytes if path == '/api/videos' else self.settings.max_image_bytes
        limit += 1024 * 1024  # Multipart headers and bounded metadata, separate from file limits.
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            declared = limit + 1
        message = 'Upload exceeds the configured request size limit.'
        if declared > limit:
            response = JSONResponse({'error': {'code': 'request_too_large', 'message': message}}, status_code=413)
            return await response(scope, receive, send)
        consumed = 0
        async def limited_receive():
            nonlocal consumed
            event = await receive()
            if event['type'] == 'http.request':
                consumed += len(event.get('body', b''))
                if consumed > limit:
                    raise AppError(413, 'request_too_large', message)
            return event
        await self.app(scope, limited_receive, send)
