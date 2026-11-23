# ruff: noqa: S101, D103, PLR2004
"""The ``brms`` command on a desktop: a second launch, a busy port, worker defaults, stopping."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

from brms.web.__main__ import _port_free, default_workers, main

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

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


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _start_lab(tmp_path: Path) -> tuple[subprocess.Popen[str], str]:
    port = _free_port()
    lab = subprocess.Popen(  # noqa: S603 (our own command)
        [sys.executable, "-m", "brms.web", "--no-browser", "--port", str(port), "--data-dir", str(tmp_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
    )
    url = f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + 60
    while True:
        try:
            with urllib.request.urlopen(url + "api/banks", timeout=2):  # noqa: S310 (local URL)
                return lab, url
        except OSError:
            if time.monotonic() > deadline or lab.poll() is not None:
                lab.kill()
                raise
            time.sleep(0.3)


def _stopped(lab: subprocess.Popen[str]) -> str:
    try:
        out, _ = lab.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(lab.pid, signal.SIGKILL)
        out, _ = lab.communicate()
        raise AssertionError("brms did not stop:\n" + out) from None
    return out


def test_ctrl_c_stops_the_lab_and_its_workers_quietly(tmp_path: Path) -> None:
    lab, _ = _start_lab(tmp_path)
    time.sleep(2)  # the demo summaries have started worker processes
    os.killpg(lab.pid, signal.SIGINT)  # what Ctrl+C in a terminal does: every process in the group
    out = _stopped(lab)
    assert lab.returncode == 0, out
    assert "Traceback" not in out, out
    assert "stopped" in out.splitlines()[-1], out


def test_quit_from_the_browser_stops_the_lab(tmp_path: Path) -> None:
    lab, url = _start_lab(tmp_path)
    request = urllib.request.Request(url + "api/quit", data=b"{}", method="POST",  # noqa: S310 (local URL)
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (local URL)
        assert response.status == 202
    out = _stopped(lab)
    assert lab.returncode == 0, out
    assert "Traceback" not in out, out
    assert "stopped" in out.splitlines()[-1], out


def test_a_port_just_released_is_free_again() -> None:
    # Stopping the lab leaves its closed connections in TIME_WAIT for up to a minute; a restart must still start.
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        client = socket.create_connection(("127.0.0.1", port))
        served, _ = listener.accept()
        served.close()  # the server closes first, so the TIME_WAIT is on the lab's port
        client.close()
    assert _port_free("127.0.0.1", port)
