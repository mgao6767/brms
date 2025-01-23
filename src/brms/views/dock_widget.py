from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QWidget


class BRMSDockWidget(QDockWidget):
    """Custom QDockWidget that behaves like a window when floating."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        # Connect signal to detect floating status change
        self.topLevelChanged.connect(self.on_floating_status_changed)

    def on_floating_status_changed(self, floating: bool) -> None:
        """Handle floating state changes."""
        if floating:
            # Make it behave like a normal window
            self.setWindowFlags(Qt.WindowType.Window)
            self.show()  # Refresh window state
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.Window)
