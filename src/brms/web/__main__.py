"""Command line: ``brms-web [--port 8765] [--data-dir DIR] [--workers N] [--no-browser]``."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

_MAX_DEFAULT_WORKERS = 4


def default_workers(cpus: int | None = None) -> int:
    """Return runs in parallel by default: one per core, leaving one free, at most four."""
    cpus = cpus or os.cpu_count() or 2
    return max(1, min(_MAX_DEFAULT_WORKERS, cpus - 1))


def _port_free(host: str, port: int) -> bool:
    """Return True if the lab could listen on *port*: bound the way uvicorn binds it.

    SO_REUSEADDR lets a restart reuse a port whose closed connections are still in TIME_WAIT. On
    Windows that option would allow sharing a port in use, and TIME_WAIT does not block a bind there.
    """
    with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET) as probe:
        if sys.platform != "win32":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def _lab_at(url: str) -> bool:
    """Return True if a stress lab already answers at *url*."""
    try:
        with urllib.request.urlopen(url + "api/scenarios", timeout=2) as response:  # noqa: S310 (local URL)
            return "kinds" in json.load(response)
    except (OSError, ValueError):
        return False


def _out(text: str, *, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    stream.write(text + "\n")
    stream.flush()


def main(argv: list[str] | None = None) -> int:
    """Serve the web app on this computer and open it in the browser."""
    parser = argparse.ArgumentParser(prog="brms-web", description="Run the BRMS Stress Lab in your browser.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to listen on (default: this computer only)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=None, help="where banks and runs are kept "
                        "(default: $BRMS_WEB_HOME or ~/.brms-web)")
    parser.add_argument("--workers", type=int, default=None,
                        help=f"scenario runs in parallel (default: {default_workers()} on this computer)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    url = f"http://{'127.0.0.1' if args.host in {'0.0.0.0', '::'} else args.host}:{args.port}/"  # noqa: S104
    if not _port_free(args.host, args.port):
        if _lab_at(url):
            _out(f"The BRMS Stress Lab is already running at {url}")
            if not args.no_browser:
                webbrowser.open(url)
            return 0
        _out(f"Port {args.port} is used by another program. Start the lab on another port, "
             f"for example: brms-web --port {args.port + 35}", err=True)
        return 1

    try:
        import uvicorn
    except ImportError:
        _out('The browser app needs its extra: pip install "brms[web]"', err=True)
        return 1
    from brms.web.app import create_app
    from brms.web.workspace import default_data_dir

    data_dir = args.data_dir or default_data_dir()
    server: uvicorn.Server | None = None

    def quit_lab() -> None:
        if server is not None:
            server.should_exit = True  # the same graceful stop as Ctrl+C

    app = create_app(data_dir, workers=args.workers or default_workers(), on_quit=quit_lab)
    server = uvicorn.Server(uvicorn.Config(app, host=args.host, port=args.port, log_level="warning",
                                           timeout_graceful_shutdown=5))
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    _out(f"BRMS Stress Lab running at {url}\nYour banks and runs are saved in {data_dir}\n"
         "Keep this window open while you use the lab. To stop it, click Quit in the lab or press Ctrl+C here.")
    with contextlib.suppress(KeyboardInterrupt):  # uvicorn re-raises Ctrl+C once it has shut down
        server.run()
    _out("The BRMS Stress Lab has stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
