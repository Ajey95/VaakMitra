"""AU-003: bound word-audio multipart bodies before Starlette parses uploads."""

from starlette.responses import JSONResponse
from starlette.formparsers import MultiPartParser, MultiPartException
from fastapi import HTTPException
from fastapi.routing import APIRoute

from ..config import settings


WORD_UPLOAD_PATHS = frozenset({"/api/v1/word-assessments", "/api/evaluate/speech", "/api/dev/word-lab/assess"})


class MemoryOnlyWordRoute(APIRoute):
    """PRV-002: valid-sized audio must not hit Starlette's 1 MiB disk spool."""
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def memory_upload(request):
            if (request.method != 'POST' or request.url.path not in WORD_UPLOAD_PATHS
                    or not request.headers.get('content-type', '').startswith('multipart/form-data')):
                return await handler(request)
            maximum = int(settings.MAX_UPLOAD_BYTES)
            parser = MultiPartParser(request.headers, request.stream(), max_files=1, max_fields=8,
                                     max_part_size=maximum)
            # The outer ASGI middleware already bounded the entire body. Configure
            # this parser instance only; unrelated uploads keep their own limits.
            parser.spool_max_size = maximum + 1
            try:
                form = await parser.parse()
            except MultiPartException:
                raise HTTPException(400, detail='invalid_audio_multipart') from None
            request._form = form
            try:
                return await handler(request)
            finally:
                await form.close()
        return memory_upload


class WordUploadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] not in WORD_UPLOAD_PATHS:
            return await self.app(scope, receive, send)

        maximum = int(settings.MAX_UPLOAD_BYTES)
        headers = dict(scope.get("headers", []))
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                if int(declared) > maximum:
                    return await self._too_large(scope, receive, send)
            except ValueError:
                return await JSONResponse({"detail": "invalid_content_length"}, status_code=400)(scope, receive, send)

        # The entire request (including multipart overhead) is bounded in memory,
        # so python-multipart never spools an oversized body to disk first.
        chunks = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > maximum:
                return await self._too_large(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        return await self.app(scope, replay, send)

    @staticmethod
    async def _too_large(scope, receive, send):
        return await JSONResponse({"detail": "audio_too_large"}, status_code=413)(scope, receive, send)
