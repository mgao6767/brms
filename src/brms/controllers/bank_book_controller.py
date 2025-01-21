from abc import ABC
from typing import TYPE_CHECKING

from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.instruments.base import Instrument
from brms.models.bank_book import BankBook, BankingBook, Position, TradingBook
from brms.views.bank_book_widget import (
    AssetColumns,
    BRMSBankBookWidget,
    BRMSBankingBookWidget,
    BRMSTradingBookWidget,
    ColumnOrder,
    LiabilityColumns,
)
from brms.views.tree_widget import QMODELINDEX, TreeModel

if TYPE_CHECKING:
    from PySide6.QtCore import QItemSelection


class BankBookController(BRMSController, ABC):
    """Controller for managing a bank's banking or trading book."""

    def __init__(self, bank_book: BankBook, view: BRMSBankBookWidget, inspector_ctrl: InspectorController) -> None:
        self.bank_book = bank_book
        self.bank_book_widget = view
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Pointers to TreeModel
        self.long_model: TreeModel = self.bank_book_widget.assets_tree.tree_model
        self.short_model: TreeModel = self.bank_book_widget.liabilities_tree.tree_model
        # Hide ID column since that instrument id is only used internally
        self.set_id_column_visibility(visible=False)
        self.connect_signals()

    @staticmethod
    def instrument_to_data(instrument: Instrument, position: Position) -> list[dict]:
        """Convert an instrument to data that can be used by the TreeModel."""
        data: dict[ColumnOrder, object]
        if position == Position.LONG:
            # Notably the dict can be constructed in any order as it will be sorted by column order required by the view
            data = {
                AssetColumns.ID: instrument.id,  # UUID is not displayable by TreeView
                AssetColumns.Asset: instrument.name,
                AssetColumns.Value: instrument.value,
            }
        elif position == Position.SHORT:
            data = {
                LiabilityColumns.ID: instrument.id,
                LiabilityColumns.Liability: instrument.name,
                LiabilityColumns.Value: instrument.value,
            }
        return [data]

    def add_instrument(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to the bank book."""
        self.bank_book.add_instrument(instrument, position)
        match position:
            case Position.LONG:
                self.long_model.add_data(QMODELINDEX, self.instrument_to_data(instrument, position))
            case Position.SHORT:
                self.short_model.add_data(QMODELINDEX, self.instrument_to_data(instrument, position))

    def remove_instrument(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from the bank book."""
        self.bank_book.remove_instrument(instrument, position)
        match position:
            case Position.LONG:
                self.long_model.remove_data(QMODELINDEX, instrument.id, id_column=AssetColumns.ID.value)
            case Position.SHORT:
                self.short_model.remove_data(QMODELINDEX, instrument.id, id_column=LiabilityColumns.ID.value)

    def set_id_column_visibility(self, *, visible: bool) -> None:
        """Set the visibility of the ID column in the tree view."""
        self.bank_book_widget.assets_tree.setColumnHidden(AssetColumns.ID.value, not visible)
        self.bank_book_widget.liabilities_tree.setColumnHidden(LiabilityColumns.ID.value, not visible)

    def on_instrument_selected(
        self,
        selected: "QItemSelection",
        deselected: "QItemSelection",
        position: Position,
    ) -> None:
        """Slot to handle selection changes."""
        if position == Position.LONG:
            indexes = self.bank_book_widget.assets_tree.selectedIndexes()
            id_column = AssetColumns.ID.value
        else:
            indexes = self.bank_book_widget.liabilities_tree.selectedIndexes()
            id_column = LiabilityColumns.ID.value
        if indexes:
            selected_index = indexes[0]
            item = selected_index.internalPointer()
            instrument_id = item.data(id_column)
            if instrument := self.bank_book.get_instrument_by_id(instrument_id):
                self.inspector_ctrl.show_instrument_details(instrument)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.bank_book_widget.assets_tree.selectionModel().selectionChanged.connect(
            lambda selected, deselected: self.on_instrument_selected(selected, deselected, Position.LONG),
        )
        self.bank_book_widget.liabilities_tree.selectionModel().selectionChanged.connect(
            lambda selected, deselected: self.on_instrument_selected(selected, deselected, Position.SHORT),
        )


class BankingBookController(BankBookController):
    """Controller for banking book."""

    def __init__(
        self,
        bank_book: BankingBook,
        view: BRMSBankingBookWidget,
        inspector_ctrl: InspectorController,
    ) -> None:
        super().__init__(bank_book, view, inspector_ctrl)

    def connect_signals(self) -> None:
        super().connect_signals()
        assert isinstance(self.bank_book_widget, BRMSBankingBookWidget)
        self.bank_book_widget.btn_loan_portfolio_overview.clicked.connect(self.on_btn_loan_portfolio_overview)
        self.bank_book_widget.btn_loan_risk_assessment.clicked.connect(self.on_btn_loan_risk_assessment)
        self.bank_book_widget.btn_htm_portfolio_analysis.clicked.connect(self.on_btn_htm_portfolio_analysis)
        self.bank_book_widget.btn_market_value_assessment.clicked.connect(self.on_btn_market_value_assessment)
        self.bank_book_widget.btn_liquidity_position.clicked.connect(self.on_btn_liquidity_position)
        self.bank_book_widget.btn_banking_book_profitability.clicked.connect(self.on_btn_banking_book_profitability)
        self.bank_book_widget.btn_asset_liability_matching.clicked.connect(self.on_btn_asset_liability_matching)
        self.bank_book_widget.btn_process_loan_applications.clicked.connect(self.on_btn_process_loan_applications)
        self.bank_book_widget.btn_modify_loan_terms.clicked.connect(self.on_btn_modify_loan_terms)
        self.bank_book_widget.btn_trade_treasury_securities.clicked.connect(self.on_btn_trade_treasury_securities)
        self.bank_book_widget.btn_trade_corporate_securities.clicked.connect(self.on_btn_trade_corporate_securities)
        self.bank_book_widget.btn_adjust_deposit_interest_rate.clicked.connect(self.on_btn_adjust_deposit_interest_rate)
        self.bank_book_widget.btn_manage_debt_instruments.clicked.connect(self.on_btn_manage_debt_instruments)

    def on_btn_loan_portfolio_overview(self) -> None:
        """Handle Loan Portfolio Overview button click."""

    def on_btn_loan_risk_assessment(self) -> None:
        """Handle Loan Risk Assessment button click."""

    def on_btn_htm_portfolio_analysis(self) -> None:
        """Handle HTM Portfolio Analysis button click."""

    def on_btn_market_value_assessment(self) -> None:
        """Handle Market Value Assessment button click."""

    def on_btn_liquidity_position(self) -> None:
        """Handle Liquidity Position button click."""

    def on_btn_banking_book_profitability(self) -> None:
        """Handle Banking Book Profitability button click."""

    def on_btn_asset_liability_matching(self) -> None:
        """Handle Asset-Liability Matching button click."""

    def on_btn_process_loan_applications(self) -> None:
        """Handle Process Loan Applications button click."""

    def on_btn_modify_loan_terms(self) -> None:
        """Handle Modify Loan Terms button click."""

    def on_btn_trade_treasury_securities(self) -> None:
        """Handle Trade Treasury Securities button click."""

    def on_btn_trade_corporate_securities(self) -> None:
        """Handle Trade Corporate Securities button click."""

    def on_btn_adjust_deposit_interest_rate(self) -> None:
        """Handle Adjust Deposit Interest Rate button click."""

    def on_btn_manage_debt_instruments(self) -> None:
        """Handle Manage Debt Instruments button click."""


class TradingBookController(BankBookController):
    """Controller for trading book."""

    def __init__(
        self,
        bank_book: TradingBook,
        view: BRMSTradingBookWidget,
        inspector_ctrl: InspectorController,
    ) -> None:
        super().__init__(bank_book, view, inspector_ctrl)

    def connect_signals(self) -> None:
        super().connect_signals()
        assert isinstance(self.bank_book_widget, BRMSTradingBookWidget)
