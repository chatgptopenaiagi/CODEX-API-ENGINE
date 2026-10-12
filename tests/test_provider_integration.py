import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from cae import CAE
from cae.access import AccessRuntime
from cae.errors import APIError
from cae.policy import PolicyEngine, Rule
from cae.providers import HTTPProvider, HTTPProviderTransport, ProviderConfig


def test_independent_local_provider_over_real_http():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append((self.path, self.headers.get("Authorization")))
            self.respond({"data": [{"id": "local-model"}]})

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, self.headers.get("Authorization")))
            assert data["model"] == "local-model"
            self.respond(
                {
                    "choices": [{"message": {"content": "local answer"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                }
            )

        def respond(self, value):
            data = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    spec = ProviderConfig(
        "local", "vllm", f"http://127.0.0.1:{server.server_port}", authenticated=False
    )
    rule = Rule(
        "local-app",
        "app",
        "local",
        "default",
        frozenset({"models", "health", "diagnostics", "chat", "usage"}),
        models=frozenset({"local-model"}),
    )

    def no_store(_):
        raise AssertionError("Local unauthenticated adapter must not read credentials")

    engine = CAE(
        app="app",
        provider="local",
        runtime=AccessRuntime((HTTPProvider(spec),), PolicyEngine((rule,)), stores=no_store),
    )
    try:
        assert engine.connect()["authentication"] == "not_required"
        assert engine.provider("local").chat("local-model", "hello")["text"] == "local answer"
        assert engine.provider("local").usage()["output_tokens"] == 3
        assert requests == [("/v1/models", None), ("/v1/chat/completions", None)]
    finally:
        engine.close()
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_trickling_provider_body_has_deadline():
    class SlowHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "100000")
            self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(0.02)
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    spec = ProviderConfig("local", "vllm", f"http://127.0.0.1:{server.server_port}",
                          authenticated=False)
    try:
        started = time.monotonic()
        with pytest.raises(APIError, match="api_request_failed"):
            HTTPProviderTransport(timeout=2, body_timeout=0.1).send(spec, "GET", "/v1/models",
                                                                 {}, None)
        assert time.monotonic() - started < 1.5
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_truncated_http_body_with_valid_json_is_not_success():
    class TruncatedHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = b'{"data": [{"id": "model"}]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body) + 50))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), TruncatedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    spec = ProviderConfig("local", "vllm", f"http://127.0.0.1:{server.server_port}",
                          authenticated=False)
    try:
        with pytest.raises(APIError, match="api_request_failed"):
            HTTPProvider(spec).request("models", "")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
