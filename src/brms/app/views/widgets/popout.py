"""Reusable pop-out helper for floating a widget into a separate window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QMainWindow

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QSplitter, QWidget


class PopOutManager(QObject):
    """Moves a widget from a QSplitter into a floating window and back.

    Usage:
        self._popout = PopOutManager(self.plot_panel, self.splitter, title="...")
        pop_action.triggered.connect(self._popout.toggle)
    """

    def __init__(self, widget: QWidget, splitter: QSplitter, title: str) -> None:
        """Initialize with the widget to float, its parent splitter, and a window title."""
        super().__init__(widget)
        self._widget = widget
        self._splitter = splitter
        self._title = title
        self._window: QMainWindow | None = None
        self._original_index: int = -1
        self._original_sizes: list[int] = []

    def toggle(self) -> None:
        """Float the widget if embedded, or raise the existing window if already floating."""
        if self._window is not None and self._window.isVisible():
            self._window.raise_()
            self._window.activateWindow()
            return
        self._float()

    def _float(self) -> None:
        """Reparent the widget into a new top-level window."""
        self._original_index = self._splitter.indexOf(self._widget)
        self._original_sizes = self._splitter.sizes()

        window = QMainWindow(None, Qt.WindowType.Window)
        window.setWindowTitle(self._title)
        window.resize(900, 600)
        window.setCentralWidget(self._widget)
        window.closeEvent = self._on_close  # type: ignore[method-assign]
        self._window = window
        window.show()

    def _on_close(self, event: QCloseEvent) -> None:
        """Reparent the widget back to the splitter when the floating window closes."""
        if self._original_index >= 0:
            self._splitter.insertWidget(self._original_index, self._widget)
            if self._original_sizes:
                self._splitter.setSizes(self._original_sizes)
        self._window = None
        event.accept()
