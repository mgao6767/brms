from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QWidget, QSplitter

from brms.views.tree_widget import BRMSTreeWidget


class ColumnOrder(Enum): ...


class AssetColumns(ColumnOrder):
    ID = 0
    Asset = 1
    Value = 2


class LiabilityColumns(ColumnOrder):
    ID = 0
    Liability = 1
    Value = 2


BANKING_BOOK_ASSET_COLUMNS = [col.name for col in AssetColumns]
BANKING_BOOK_LIABILITY_COLUMNS = [col.name for col in LiabilityColumns]
TRADING_BOOK_ASSET_COLUMNS = [col.name for col in AssetColumns]
TRADING_BOOK_LIABILITY_COLUMNS = [col.name for col in LiabilityColumns]


class BRMSBankBookWidget(QWidget):
    def __init__(
        self,
        asset_columns: list[str],
        liability_columns: list[str],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.assets_tree = BRMSTreeWidget(asset_columns)
        self.liabilities_tree = BRMSTreeWidget(liability_columns)

        # Control panel
        ctrl_panel = QSplitter()
        ctrl_panel.setOrientation(Qt.Orientation.Vertical)
        analysis_group = QGroupBox("Analysis")
        management_group = QGroupBox("Management")
        ctrl_panel.addWidget(analysis_group)
        ctrl_panel.addWidget(management_group)

        # Create a splitter to display the tree views side by side
        splitter = QSplitter()
        splitter.addWidget(self.assets_tree)
        splitter.addWidget(self.liabilities_tree)

        # Create a layout for the widget and add the splitter
        book_layout = QHBoxLayout()
        book_layout.addWidget(ctrl_panel)
        book_layout.addWidget(splitter)
        self.setLayout(book_layout)


class BRMSBankingBookWidget(BRMSBankBookWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            asset_columns=BANKING_BOOK_ASSET_COLUMNS,
            liability_columns=BANKING_BOOK_LIABILITY_COLUMNS,
            parent=parent,
        )


class BRMSTradingBookWidget(BRMSBankBookWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            asset_columns=TRADING_BOOK_ASSET_COLUMNS,
            liability_columns=TRADING_BOOK_LIABILITY_COLUMNS,
            parent=parent,
        )
