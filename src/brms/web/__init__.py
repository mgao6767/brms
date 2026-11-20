"""The stress-test lab in a browser: a FastAPI server over :mod:`brms.lab` and a static front end.

Run ``brms-web`` (or ``python -m brms.web``) after ``pip install "brms[web]"``.
"""

from brms.web.app import create_app

__all__ = ["create_app"]
