"""Command line: ``brms-web [--port 8765] [--data-dir DIR] [--workers 2] [--no-browser]``."""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Serve the web app and open it in the browser."""
    parser = argparse.ArgumentParser(prog="brms-web", description="Serve the BRMS stress-test lab in a browser.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to listen on (0.0.0.0 for a server)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=None, help="where banks and runs are kept "
                        "(default: $BRMS_WEB_HOME or ~/.brms-web)")
    parser.add_argument("--workers", type=int, default=2, help="scenario runs in parallel")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError:
        sys.stderr.write('The web app needs its extra: pip install "brms[web]"\n')
        return 1
    from brms.web.app import create_app

    app = create_app(args.data_dir, workers=args.workers)
    url = f"http://{'127.0.0.1' if args.host in {'0.0.0.0', '::'} else args.host}:{args.port}/"  # noqa: S104
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    sys.stdout.write(f"BRMS Stress Lab at {url} (Ctrl+C to stop)\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
