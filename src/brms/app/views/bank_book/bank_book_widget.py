"""Base bank book widget."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QSplitter,
    QWidget,
)

from brms.app.views.bank_book.columns import AssetColumns, LiabilityColumns
from brms.app.views.bank_book.delegates import CurrencyDelegate, CustomHeader, InstrumentIDDelegate
from brms.app.views.widgets.tree_widget import BRMSTreeWidget


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

        # fmt: off
        # Replace the default header with our custom header
        header = CustomHeader(Qt.Orientation.Horizontal, self.assets_tree)
        self.assets_tree.setHeader(header)
        self.assets_tree.header().setSectionResizeMode(AssetColumns.Asset.value, QHeaderView.ResizeMode.Stretch)
        self.assets_tree.header().setSectionResizeMode(AssetColumns.Value.value, QHeaderView.ResizeMode.ResizeToContents)
        header_liabilities = CustomHeader(Qt.Orientation.Horizontal, self.assets_tree)
        self.liabilities_tree.setHeader(header_liabilities)
        self.liabilities_tree.header().setSectionResizeMode(LiabilityColumns.Liability.value, QHeaderView.ResizeMode.Stretch)
        self.liabilities_tree.header().setSectionResizeMode(LiabilityColumns.Value.value, QHeaderView.ResizeMode.ResizeToContents)
        # fmt: on

        # fmt: off
        # Set format delegate for the "value" column
        # Note: parent of the delegate must be set or otherwise the app will crash!
        self.assets_tree.setItemDelegateForColumn(AssetColumns.Value.value, CurrencyDelegate(self.assets_tree))
        self.liabilities_tree.setItemDelegateForColumn(LiabilityColumns.Value.value, CurrencyDelegate(self.liabilities_tree))
        # Set format delegate for the "id" column
        self.assets_tree.setItemDelegateForColumn(AssetColumns.ID.value, InstrumentIDDelegate(self.assets_tree))
        self.liabilities_tree.setItemDelegateForColumn(LiabilityColumns.ID.value, InstrumentIDDelegate(self.liabilities_tree))
        # fmt: on

        # Control panel
        ctrl_panel = QSplitter()
        ctrl_panel.setOrientation(Qt.Orientation.Vertical)
        self.analysis_group = QGroupBox("Analysis")
        self.management_group = QGroupBox("Management")
        ctrl_panel.addWidget(self.analysis_group)
        ctrl_panel.addWidget(self.management_group)
        ctrl_panel.setStretchFactor(0, 0)  # Top widget (analysis group) does not stretch
        ctrl_panel.setStretchFactor(1, 1)  # Bottom widget (mgmt group) expands

        # Create a splitter to display the tree views side by side
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self.assets_tree)
        splitter.addWidget(self.liabilities_tree)

        # Create a layout for the widget and add the splitter
        main_splitter = QSplitter()
        main_splitter.setOrientation(Qt.Orientation.Horizontal)
        main_splitter.addWidget(ctrl_panel)
        main_splitter.addWidget(splitter)
        main_splitter.setStretchFactor(0, 0)  # Left widget (control panel) does not stretch
        main_splitter.setStretchFactor(1, 1)  # Right widget (splitter with tree views) expands
        main_layout = QHBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
