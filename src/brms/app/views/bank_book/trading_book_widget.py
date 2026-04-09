"""Trading book widget."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from brms.app.views.bank_book.bank_book_widget import BRMSBankBookWidget
from brms.app.views.bank_book.columns import TRADING_BOOK_ASSET_COLUMNS, TRADING_BOOK_LIABILITY_COLUMNS


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
