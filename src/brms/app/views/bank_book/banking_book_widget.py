"""Banking book widget."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from brms.app.views.bank_book.bank_book_widget import BRMSBankBookWidget
from brms.app.views.bank_book.columns import BANKING_BOOK_ASSET_COLUMNS, BANKING_BOOK_LIABILITY_COLUMNS


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
