"""Small local/public-demo boundary; no session or authentication architecture."""
import ntpath

from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles


class LocalStaticFiles(StaticFiles):
    def lookup_path(self, path: str):
        # Reject Windows absolute/UNC/device paths before realpath can contact SMB.
        # Keep the inherited containment/symlink checks for ordinary local paths.
        if '\\' in path or ntpath.splitdrive(path)[0] or path.startswith('/'):
            return '', None
        return super().lookup_path(path)


class RequestBoundary:
    """Validate raw URL inputs and bound JSON bodies before framework parsing."""
    def __init__(self, app, max_body_bytes: int = 2_000_000):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path = scope.get('path', '')
        hosts = [value for key, value in scope.get('headers', []) if key.lower() == b'host']
        if (not path.startswith('/') or '\\' in path or len(hosts) > 1 or
                any(any(c in host for c in (b'/', b'\\', b'?', b'#', b'@')) for host in hosts)):
            return await JSONResponse({'detail': 'invalid request target'}, status_code=400)(scope, receive, send)
        if scope.get('method') not in ('POST', 'PUT', 'PATCH'):
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > self.max_body_bytes:
                return await JSONResponse({'detail': 'request body exceeds configured limit'}, status_code=413)(scope, receive, send)
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        body = b''.join(chunks)
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()

        return await self.app(scope, bounded_receive, send)
