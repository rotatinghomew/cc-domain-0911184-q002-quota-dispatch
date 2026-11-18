import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Platform:
    def __init__(self):
        self.tokens = {'alpha': 'alpha-v1', 'beta': 'beta-v1'}
        self.generation = {'alpha': 1, 'beta': 1}
        self.remaining = 20
        self.reset_at = 60
        self.now = 0
        self.calls = []
        self.lock = threading.Lock()

    def asset(self, tenant, token, asset):
        self.calls.append({'tenant': tenant, 'token': token, 'asset': asset, 'at': self.now})
        if token != self.tokens.get(tenant):
            return 401, {}, {'error': 'session_expired'}
        if self.now >= self.reset_at:
            self.remaining = 20
            self.reset_at = self.now + 60
        if self.remaining <= 0:
            return 429, {'Retry-After': str(self.reset_at - self.now), 'X-Quota-Reset': str(self.reset_at)}, {'error': 'quota_exhausted'}
        self.remaining -= 1
        return 200, {'X-Quota-Remaining': str(self.remaining), 'X-Quota-Reset': str(self.reset_at)}, {
            'tenant': tenant, 'asset': asset, 'content': 'media-' + asset,
            'session_generation': self.generation[tenant],
        }


@contextmanager
def serve(platform=None):
    platform = platform or Platform()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if not self.path.startswith('/asset/'):
                self.send_error(404)
                return
            with platform.lock:
                status, headers, payload = platform.asset(
                    self.headers.get('X-Tenant'), self.headers.get('Authorization'), self.path[7:])
            self.reply(status, headers, payload)

        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length))
            tenant = payload.get('tenant')
            if self.path != '/session' or tenant not in platform.tokens:
                self.reply(400, {}, {'error': 'unknown_tenant'})
                return
            with platform.lock:
                platform.generation[tenant] += 1
                platform.tokens[tenant] = f'{tenant}-v{platform.generation[tenant]}'
                token = platform.tokens[tenant]
            self.reply(200, {}, {'token': token, 'generation': platform.generation[tenant]})

        def reply(self, status, headers, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', platform
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
