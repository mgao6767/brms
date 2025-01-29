import uuid
from enum import IntEnum

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStyledItemDelegate,
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
    Value = 2


class LiabilityColumns(ColumnOrder):
    ID = 0
    Liability = 1
    Value = 2


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
        layout.addWidget(QLabel("Investment Securities (HTM & FVOCI)"))
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
        layout_mgmt.addWidget(QLabel("Investment Securities (HTM & FVOCI)"))
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
