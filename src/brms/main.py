"""Main module for the BRMS application."""

import sys

from brms.core.services import build_core_services


def main() -> None:
    """Run the main entry point for the BRMS application."""
    from brms.app.application import App

    services = build_core_services()
    app = App(sys.argv, services)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
