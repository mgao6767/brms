# ruff: noqa: S101, D103, PLR2004
"""The ``brms-web`` command on a desktop: a second launch, a busy port, worker defaults."""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

from brms.web.__main__ import default_workers, main

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pytest


class _Lab(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = json.dumps({"kinds": ["historical"]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        pass


def _serve() -> Iterator[int]:
    server = HTTPServer(("127.0.0.1", 0), _Lab)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()


def test_a_second_launch_points_to_the_running_lab(capsys: pytest.CaptureFixture[str]) -> None:
    for port in _serve():
        assert main(["--port", str(port), "--no-browser"]) == 0
    assert "already running" in capsys.readouterr().out


def test_a_port_taken_by_another_program_says_how_to_move(capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as other:
        other.bind(("127.0.0.1", 0))
        other.listen()
        port = other.getsockname()[1]
        assert main(["--port", str(port), "--no-browser"]) == 1
    assert "--port" in capsys.readouterr().err


def test_default_workers_leave_a_core_free() -> None:
    assert default_workers(1) == 1
    assert default_workers(2) == 1
    assert default_workers(8) == 4
