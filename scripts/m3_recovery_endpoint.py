"""Disposable loopback fault injector. Never used on the operator's Qwen port."""

import argparse
import json
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if args.port == 8080:
        parser.error("operator endpoint forbidden")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            pass

        def do_POST(self) -> None:
            try:
                assert self.path == "/v1/chat/completions"
                assert not self.headers.get("Authorization")
                length = int(self.headers.get("Content-Length", "0"))
                assert 0 < length <= 65536
                payload = json.loads(self.rfile.read(length))
                mode = (args.state / "mode.txt").read_text().strip()
                with (args.state / "calls.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"model": payload["model"], "mode": mode}) + "\n")
                if mode in {"terminate", "provider_timeout"}:
                    time.sleep(30)
                if mode == "late":
                    time.sleep(1.5)
                if mode == "reset":
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                value: dict[str, Any] = {"model": payload["model"], "choices": [{"message": {
                    "role": "assistant", "content": "DELAYED_FINAL" if mode == "late" else "SYNTHETIC_FINAL",
                    "reasoning_content": "PRIVATE_REASONING_CANARY"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3}}
                status = 200
                if mode == "wrong_model":
                    value["model"] = "unapproved"
                elif mode == "missing":
                    del value["choices"]
                elif mode == "wrong_type":
                    value["choices"][0]["message"]["content"] = []
                elif mode == "usage":
                    value["usage"]["prompt_tokens"] = True
                elif mode == "oversized_output":
                    value["choices"][0]["message"]["content"] = "x" * 9000
                elif mode == "error":
                    status = 503
                    value = {"error": "sk-synthetic-provider-error-canary"}
                body = json.dumps(value).encode()
                if mode == "json":
                    body = b"{invalid"
                elif mode == "oversized_body":
                    body = b"x" * (4 * 1024 * 1024 + 1)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body) + (50 if mode == "truncated" else 0)))
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                self.close_connection = True
            except (OSError, ValueError, AssertionError):
                self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    (args.state / "ready.json").write_text(json.dumps({"port": server.server_port}))
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
