"""Register bundled IBM Plex font files with Qt and matplotlib."""

from __future__ import annotations

from importlib.resources import as_file, files

import matplotlib as mpl
from matplotlib import font_manager
from PySide6.QtGui import QFontDatabase

from brms.core.exceptions import BRMSError

_FONT_FILES = (
    "IBMPlexSans-Light.ttf",
    "IBMPlexSans-LightItalic.ttf",
    "IBMPlexSans-Regular.ttf",
    "IBMPlexSans-Italic.ttf",
    "IBMPlexSans-SemiBold.ttf",
    "IBMPlexSans-SemiBoldItalic.ttf",
    "IBMPlexMono-Regular.ttf",
    "IBMPlexMono-Italic.ttf",
)


def load_bundled_fonts() -> None:
    """Register every bundled IBM Plex TTF with Qt and matplotlib.

    Must run after ``QApplication`` is constructed and before any widget
    renders. Also updates matplotlib ``rcParams`` so Figures instantiated
    later pick up Plex without needing per-plot overrides. Raises
    :class:`BRMSError` if a font file is missing or Qt rejects it.
    """
    font_dir = files("brms.resources").joinpath("fonts")
    for name in _FONT_FILES:
        with as_file(font_dir.joinpath(name)) as path:
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id == -1:
                msg = f"Failed to register bundled font: {name}"
                raise BRMSError(msg)
            font_manager.fontManager.addfont(str(path))

    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = [
        "IBM Plex Sans",
        "Helvetica Neue",
        "Arial",
        "DejaVu Sans",
    ]
    mpl.rcParams["font.monospace"] = [
        "IBM Plex Mono",
        "Menlo",
        "Courier",
        "DejaVu Sans Mono",
    ]
