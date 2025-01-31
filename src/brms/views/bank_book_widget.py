import uuid
from enum import IntEnum

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionHeader,
    QVBoxLayout,
    QWidget,
)

from brms.views.tree_widget import BRMSTreeWidget, OldValueRole


class ColumnOrder(IntEnum):
    """Base class for column order enumerations.

    IntEnum is used to enable sorting.
    """


class AssetColumns(ColumnOrder):
    ID = 0
    Asset = 1
    Class = 2
    Value = 3


class LiabilityColumns(ColumnOrder):
    ID = 0
    Liability = 1
    Class = 2
    Value = 3


BANKING_BOOK_ASSET_COLUMNS = [col.name for col in AssetColumns]
BANKING_BOOK_LIABILITY_COLUMNS = [col.name for col in LiabilityColumns]
TRADING_BOOK_ASSET_COLUMNS = [col.name for col in AssetColumns]
TRADING_BOOK_LIABILITY_COLUMNS = [col.name for col in LiabilityColumns]


LOCALE = QLocale.system()


class CurrencyDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value, locale):
        """Format numbers as currency."""
        if isinstance(value, int | float):
            return LOCALE.toCurrencyString(value)
        return str(value)

    def paint(self, painter, option, index):
        """Customize text color for a specific column."""
        current_value = index.data(Qt.DisplayRole)
        old_value = index.data(OldValueRole)  # Get previous value from model
        if isinstance(current_value, int | float) and isinstance(old_value, int | float):
            if current_value >= old_value:
                option.palette.setColor(QPalette.Text, QColor("green"))  # Increased value
            elif current_value < old_value:
                option.palette.setColor(QPalette.Text, QColor("red"))  # Decreased value
        super().paint(painter, option, index)


class InstrumentIDDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        """Format UUID as str."""
        if isinstance(value, uuid.UUID):
            return str(value)
        return super().displayText(value, locale)  # Default behavior


class CustomHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Default left alignment
        self.text_padding = None  # Store dynamically calculated padding

    def paintSection(self, painter, rect, logicalIndex):
        """Preserve default styling but right-align the last column header text."""
        option = QStyleOptionHeader()
        self.initStyleOption(option)  # Get default styling
        option.rect = rect  # Set section rectangle
        option.section = logicalIndex  # Apply correct section index

        if logicalIndex < self.model().columnCount() - 1:
            # Store the text padding from a normal column (first column)
            super().paintSection(painter, rect, logicalIndex)

            if self.text_padding is None:  # Extract padding from the first column once
                text_rect = self.style().subElementRect(QStyle.SE_HeaderLabel, option, self)
                self.text_padding = text_rect.left() - rect.left()  # Extract left padding
        else:
            option.text = ""  # Remove default text drawing
            self.style().drawControl(QStyle.CE_HeaderSection, option, painter, self)  # Draw default header without text

            # Retrieve header text
            text = self.model().headerData(logicalIndex, Qt.Horizontal, Qt.DisplayRole)
            if text and self.text_padding is not None:
                painter.save()
                painter.setPen(self.palette().color(self.foregroundRole()))  # Keep text color

                # Apply the same padding as other columns (text_padding is dynamically calculated)
                adjusted_rect = rect.adjusted(self.text_padding, 0, -self.text_padding, 0)
                painter.drawText(adjusted_rect, Qt.AlignRight | Qt.AlignVCenter, text)

                painter.restore()


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


class BRMSBankingBookWidget(BRMSBankBookWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            asset_columns=BANKING_BOOK_ASSET_COLUMNS,
            liability_columns=BANKING_BOOK_LIABILITY_COLUMNS,
            parent=parent,
        )
        # UI components
        self.btn_loan_portfolio_overview = QPushButton("Loan Portfolio Overview")
        self.btn_loan_risk_assessment = QPushButton("Loan Risk Assessment")
        self.btn_htm_portfolio_analysis = QPushButton("HTM Portfolio Analysis")
        self.btn_market_value_assessment = QPushButton("Market Value Assessment")
        self.btn_liquidity_position = QPushButton("Liquidity Position")
        self.btn_banking_book_profitability = QPushButton("Banking Book Profitability")
        self.btn_asset_liability_matching = QPushButton("Asset-Liability Matching")
        self.btn_process_loan_applications = QPushButton("Process Loan Applications")
        self.btn_modify_loan_terms = QPushButton("Modify Loan Terms")
        self.btn_trade_treasury_securities = QPushButton("Trade Treasury Securities")
        self.btn_trade_corporate_securities = QPushButton("Trade Corporate Securities")
        self.btn_adjust_deposit_interest_rate = QPushButton("Adjust Deposit Interest Rate")
        self.btn_manage_debt_instruments = QPushButton("Manage Debt Instruments")
        # Disable all buttons
        self.btn_loan_portfolio_overview.setEnabled(False)
        self.btn_loan_risk_assessment.setEnabled(False)
        self.btn_htm_portfolio_analysis.setEnabled(False)
        self.btn_market_value_assessment.setEnabled(False)
        self.btn_liquidity_position.setEnabled(False)
        self.btn_banking_book_profitability.setEnabled(False)
        self.btn_asset_liability_matching.setEnabled(False)
        self.btn_process_loan_applications.setEnabled(False)
        self.btn_modify_loan_terms.setEnabled(False)
        self.btn_trade_treasury_securities.setEnabled(False)
        self.btn_trade_corporate_securities.setEnabled(False)
        self.btn_adjust_deposit_interest_rate.setEnabled(False)
        self.btn_manage_debt_instruments.setEnabled(False)
        # Actions
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Control panel: analysis group box
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(QLabel("Loans & Advances"))
        layout.addWidget(self.btn_loan_portfolio_overview)
        layout.addWidget(self.btn_loan_risk_assessment)
        layout.addWidget(QLabel("Investment Securities"))
        layout.addWidget(self.btn_htm_portfolio_analysis)
        layout.addWidget(self.btn_market_value_assessment)
        layout.addWidget(QLabel("Liquidity & Performance"))
        layout.addWidget(self.btn_liquidity_position)
        layout.addWidget(self.btn_banking_book_profitability)
        layout.addWidget(self.btn_asset_liability_matching)
        self.analysis_group.setLayout(layout)
        # Control panel: management group box
        layout_mgmt = QVBoxLayout()
        layout_mgmt.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout_mgmt.addWidget(QLabel("Loans & Advances"))
        layout_mgmt.addWidget(self.btn_process_loan_applications)
        layout_mgmt.addWidget(self.btn_modify_loan_terms)
        layout_mgmt.addWidget(QLabel("Investment Securities"))
        layout_mgmt.addWidget(self.btn_trade_treasury_securities)
        layout_mgmt.addWidget(self.btn_trade_corporate_securities)
        layout_mgmt.addWidget(QLabel("Deposits & Other Liabilities"))
        layout_mgmt.addWidget(self.btn_adjust_deposit_interest_rate)
        layout_mgmt.addWidget(self.btn_manage_debt_instruments)
        self.management_group.setLayout(layout_mgmt)


class BRMSTradingBookWidget(BRMSBankBookWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            asset_columns=TRADING_BOOK_ASSET_COLUMNS,
            liability_columns=TRADING_BOOK_LIABILITY_COLUMNS,
            parent=parent,
        )
        # UI components
        self.btn_trading_portfolio_overview = QPushButton("Trading Portfolio Overview")
        self.btn_risk_assessment = QPushButton("Market Risk Assessment")
        self.btn_mark_to_market_analysis = QPushButton("Mark-to-Market Analysis")
        self.btn_trading_profitability = QPushButton("Trading Profitability")
        self.btn_trade_treasury_securities = QPushButton("Trade Treasury Securities")
        self.btn_trade_corporate_securities = QPushButton("Trade Corporate Securities")
        self.btn_trade_derivatives = QPushButton("Trade Derivatives")
        # Disable all buttons
        self.btn_trading_portfolio_overview.setEnabled(False)
        self.btn_risk_assessment.setEnabled(False)
        self.btn_mark_to_market_analysis.setEnabled(False)
        self.btn_trading_profitability.setEnabled(False)
        self.btn_trade_treasury_securities.setEnabled(False)
        self.btn_trade_corporate_securities.setEnabled(False)
        self.btn_trade_derivatives.setEnabled(False)
        # Actions
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Control panel: analysis group box
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(QLabel("Trading Portfolio"))
        layout.addWidget(self.btn_trading_portfolio_overview)
        layout.addWidget(self.btn_risk_assessment)
        layout.addWidget(self.btn_mark_to_market_analysis)
        layout.addWidget(QLabel("Performance"))
        layout.addWidget(self.btn_trading_profitability)
        self.analysis_group.setLayout(layout)
        # Control panel: management group box
        layout_mgmt = QVBoxLayout()
        layout_mgmt.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout_mgmt.addWidget(QLabel("Trading Portfolio"))
        layout_mgmt.addWidget(self.btn_trade_treasury_securities)
        layout_mgmt.addWidget(self.btn_trade_corporate_securities)
        layout_mgmt.addWidget(self.btn_trade_derivatives)
        self.management_group.setLayout(layout_mgmt)
