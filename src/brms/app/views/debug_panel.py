"""Debug panel — visible only when BRMS_DEBUG=true."""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from PySide6.QtGui import QShowEvent


class DebugPanel(QWidget):
    """Floating panel with dev shortcuts, including a simulation-zip picker."""

    simulation_selected = Signal(object)  # emits Path

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the debug panel."""
        super().__init__(parent, Qt.WindowType.Window)
        self.resize(320, 360)
        self.setWindowTitle("Debug Panel")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(QLabel("Simulations (src/brms/data/*.zip)"))
        self.sim_list = QListWidget()
        self.sim_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.sim_list, 1)

        self.btn_load = QPushButton("Load Selected Simulation")
        self.btn_load.clicked.connect(self._on_load_clicked)
        layout.addWidget(self.btn_load)

        self.refresh()

    def refresh(self) -> None:
        """Rescan the data folder and repopulate the simulation list."""
        self.sim_list.clear()
        try:
            data_dir = importlib.resources.files("brms.data")
        except (ModuleNotFoundError, FileNotFoundError):
            return
        zips = sorted(
            (Path(str(entry)) for entry in data_dir.iterdir() if str(entry).endswith(".zip")),
            key=lambda p: p.name.lower(),
        )
        for path in zips:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(str(path))
            self.sim_list.addItem(item)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        """Refresh the list every time the panel is shown."""
        self.refresh()
        super().showEvent(event)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Emit the selected simulation path on double-click."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(path, Path):
            self.simulation_selected.emit(path)

    def _on_load_clicked(self) -> None:
        """Emit the selected simulation path from the Load button."""
        item = self.sim_list.currentItem()
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(path, Path):
            self.simulation_selected.emit(path)
