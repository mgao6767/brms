"""Main module for the BRMS application."""

import sys

from brms.core.services import build_core_services


def main() -> None:
    """Run the main entry point for the BRMS application."""
    try:
        import PySide6  # noqa: F401
    except ImportError:
        sys.stderr.write('The BRMS desktop app needs the GUI extra: pip install "brms[gui]"\n')
        sys.exit(1)
    from brms.app.application import App

    services = build_core_services()
    app = App(sys.argv, services)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
