"""Reusable pop-out helper for floating a widget into a separate window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QMainWindow

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QSplitter, QWidget


class PopOutManager(QObject):
    """Moves a widget from a QSplitter into a floating window and back.

    Usage:
        self._popout = PopOutManager(self.plot_panel, self.splitter, title="...")
        pop_action.triggered.connect(self._popout.toggle)
        self._popout.popped_out.connect(self.some_toolbar.setVisible)
    """

    popped_out = Signal(bool)  # True → floating, False → reparented back

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
        """Reparent the widget into a new top-level window owned by the main window."""
        self._original_index = self._splitter.indexOf(self._widget)
        self._original_sizes = self._splitter.sizes()

        # Parent = main window → popup closes automatically when the app exits
        owner = self._widget.window()
        window = QMainWindow(owner, Qt.WindowType.Window)
        window.setWindowTitle(self._title)
        window.resize(900, 600)
        window.setCentralWidget(self._widget)
        window.closeEvent = self._on_close  # type: ignore[method-assign]
        self._window = window
        window.show()
        self.popped_out.emit(True)

    def _on_close(self, event: QCloseEvent) -> None:
        """Reparent the widget back to the splitter when the floating window closes."""
        if self._original_index >= 0:
            self._splitter.insertWidget(self._original_index, self._widget)
            if self._original_sizes:
                self._splitter.setSizes(self._original_sizes)
        self._window = None
        self.popped_out.emit(False)
        event.accept()
