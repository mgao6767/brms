"""Controller for managing bank book tree widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms import DEBUG_MODE
from brms.app.controllers.base import BRMSController
from brms.app.views.bank_book import BRMSBankBookWidget, BRMSBankingBookWidget, BRMSTradingBookWidget
from brms.app.views.bank_book.columns import AssetColumns, ColumnOrder, LiabilityColumns
from brms.app.views.widgets.tree_widget import QMODELINDEX, TreeModel
from brms.core.enums import BookType
from brms.core.enums import PositionSide as Position
from brms.core.events import ValuationsUpdated
from brms.core.models.instruments.deposits import Cash

if TYPE_CHECKING:
    from brms.app.controllers.inspector_controller import InspectorController
    from brms.core.events import EventBus
    from brms.core.models.bank import BookView
    from brms.core.models.instruments.base import Instrument
    from brms.core.stores.position_store import PositionStore


class BankBookController(BRMSController):
    """Controller for managing a bank's banking or trading book."""

    def __init__(  # noqa: PLR0913
        self,
        bank_book: BookView,
        view: BRMSBankBookWidget,
        inspector_ctrl: InspectorController,
        event_bus: EventBus,
        book_type: BookType,
        position_store: PositionStore,
    ) -> None:
        """Initialize the bank book controller."""
        self.bank_book = bank_book
        self.bank_book_widget = view
        self.inspector_ctrl = inspector_ctrl
        self._book_type = book_type
        self._position_store = position_store
        # Pointers to TreeModel
        self.long_model: TreeModel = self.bank_book_widget.assets_tree.tree_model
        self.short_model: TreeModel = self.bank_book_widget.liabilities_tree.tree_model
        # Hide ID column since that instrument id is only used internally
        self.set_id_column_visibility(visible=DEBUG_MODE)
        event_bus.subscribe(ValuationsUpdated, self._on_valuations_updated)
        self.connect_signals()

    def _on_valuations_updated(self, event: ValuationsUpdated) -> None:
        """Update instrument values from valuation event."""
        for pos in self._position_store.by_book(self._book_type):
            val = event.valuations.get(pos.id)
            if val is not None and float(val) != 0:
                self.update_instrument_value(pos.instrument_id, float(val))

    @staticmethod
    def instrument_to_data(
        instrument: Instrument,
        position: Position,
        initial_value: float | None = None,
        instrument_class: object | None = None,
    ) -> list[dict]:
        """Convert an instrument to data that can be used by the TreeModel."""
        value = initial_value if initial_value is not None else getattr(instrument, "face_value", 0)
        inst_class = instrument_class or getattr(instrument, "instrument_class", None)
        class_label = inst_class.name if inst_class is not None else ""
        data: dict[ColumnOrder, object]
        if position == Position.LONG:
            data = {
                AssetColumns.ID: instrument.id,
                AssetColumns.Asset: instrument.name,
                AssetColumns.Value: value,
                AssetColumns.Class: class_label,
            }
        elif position == Position.SHORT:
            data = {
                LiabilityColumns.ID: instrument.id,
                LiabilityColumns.Liability: instrument.name,
                LiabilityColumns.Value: value,
                LiabilityColumns.Class: class_label,
            }
        return [data]

    def add_instrument(
        self,
        instrument: Instrument,
        position: Position | None = None,
        initial_value: float | None = None,
        instrument_class: object | None = None,
    ) -> None:
        """Add an instrument to the tree model."""
        if position is None:
            position = Position.LONG
        match position:
            case Position.LONG:
                self.long_model.add_data(
                    QMODELINDEX,
                    self.instrument_to_data(instrument, position, initial_value, instrument_class),
                )
            case Position.SHORT:
                self.short_model.add_data(
                    QMODELINDEX,
                    self.instrument_to_data(instrument, position, initial_value, instrument_class),
                )

    def remove_instrument(self, instrument: Instrument, position: Position | None = None) -> None:
        """Remove an instrument from the tree model."""
        if position is None:
            position = Position.LONG
        match position:
            case Position.LONG:
                self.long_model.remove_data(QMODELINDEX, instrument.id, id_column=AssetColumns.ID.value)
            case Position.SHORT:
                self.short_model.remove_data(QMODELINDEX, instrument.id, id_column=LiabilityColumns.ID.value)

    def update_instrument(self, instrument: Instrument, position: Position | None = None) -> None:
        """Update an instrument's display in the tree model."""
        if position is None:
            position = Position.LONG
        face_value = getattr(instrument, "face_value", 0)
        match position:
            case Position.LONG:
                if index := self.long_model.find_data(instrument.id, AssetColumns.ID.value):
                    self.long_model.update_data(index, {AssetColumns.Value: face_value})
            case Position.SHORT:
                if index := self.short_model.find_data(instrument.id, LiabilityColumns.ID.value):
                    self.short_model.update_data(index, {LiabilityColumns.Value: face_value})

    def update_instrument_value(self, instrument_id: str, value: float) -> None:
        """Update the displayed value for an instrument by its ID."""
        if index := self.long_model.find_data(instrument_id, AssetColumns.ID.value):
            self.long_model.update_data(index, {AssetColumns.Value: value})
        elif index := self.short_model.find_data(instrument_id, LiabilityColumns.ID.value):
            self.short_model.update_data(index, {LiabilityColumns.Value: value})

    def set_id_column_visibility(self, *, visible: bool) -> None:
        """Set the visibility of the ID column in the tree view."""
        self.bank_book_widget.assets_tree.setColumnHidden(AssetColumns.ID.value, not visible)
        self.bank_book_widget.liabilities_tree.setColumnHidden(LiabilityColumns.ID.value, not visible)

    def on_instrument_selected(self, position: Position) -> None:
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
            if instrument := self.bank_book.get_instrument_by_id(instrument_id):  # read-only, does not modify bank book
                self.inspector_ctrl.show_instrument_details(instrument)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        # When selection changed or focused changed, update inspector
        self.bank_book_widget.assets_tree.selectionModel().selectionChanged.connect(
            lambda _s, _d: self.on_instrument_selected(Position.LONG),
        )
        self.bank_book_widget.liabilities_tree.selectionModel().selectionChanged.connect(
            lambda _s, _d: self.on_instrument_selected(Position.SHORT),
        )
        self.bank_book_widget.assets_tree.focused.connect(lambda: self.on_instrument_selected(Position.LONG))
        self.bank_book_widget.liabilities_tree.focused.connect(lambda: self.on_instrument_selected(Position.SHORT))


class BankingBookController(BankBookController):
    """Controller for banking book."""

    def __init__(  # noqa: PLR0913
        self,
        bank_book: BookView,
        view: BRMSBankingBookWidget,
        inspector_ctrl: InspectorController,
        event_bus: EventBus,
        book_type: BookType,
        position_store: PositionStore,
    ) -> None:
        """Initialize the banking book controller."""
        super().__init__(bank_book, view, inspector_ctrl, event_bus, book_type, position_store)
        self.bank_book_widget.liabilities_tree.setColumnHidden(LiabilityColumns.Class.value, hidden=True)

    def _add_cash(self, cash: Cash) -> None:
        # Check if there is already cash instrument in the tree's model
        idx = self.long_model.find_data("Cash", column=AssetColumns.Asset)  # noqa: FIX002, TD002, TD003  # TODO: improve
        # Not found, add it to the tree's model
        if idx is None:
            self.long_model.add_data(QMODELINDEX, self.instrument_to_data(cash, Position.LONG))
            return
        if not idx.isValid():
            return
        # Found existing cash record in the model
        item = idx.internalPointer()
        cash_id = item.data(AssetColumns.ID.value)
        # Obtain a reference to the cash instrument
        cash_instrument = self.bank_book.get_instrument_by_id(cash_id)
        if isinstance(cash_instrument, Cash):
            self.long_model.update_data(idx, {AssetColumns.Value: cash_instrument.value})

    def _remove_cash(self, _cash: Cash) -> None:
        idx = self.long_model.find_data("Cash", column=AssetColumns.Asset)  # noqa: FIX002, TD002, TD003  # TODO: improve
        if idx is None:
            msg = "No cash in the asset tree model"
            raise ValueError(msg)
        if not idx.isValid():
            return
        # Found existing cash record in the model
        item = idx.internalPointer()
        cash_id = item.data(AssetColumns.ID.value)
        cash_instrument = self.bank_book.get_instrument_by_id(cash_id)
        if isinstance(cash_instrument, Cash):
            self.long_model.update_data(idx, {AssetColumns.Value: cash_instrument.value})

    def add_instrument(
        self,
        instrument: Instrument,
        position: Position | None = None,
        initial_value: float | None = None,
        instrument_class: object | None = None,
    ) -> None:
        """Add an instrument to the tree model."""
        if isinstance(instrument, Cash):
            self._add_cash(instrument)
            return
        super().add_instrument(instrument, position, initial_value=initial_value, instrument_class=instrument_class)

    def remove_instrument(self, instrument: Instrument, position: Position | None = None) -> None:
        """Remove an instrument from the tree model."""
        if isinstance(instrument, Cash):
            self._remove_cash(instrument)
            return
        super().remove_instrument(instrument, position)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        super().connect_signals()
        assert isinstance(self.bank_book_widget, BRMSBankingBookWidget)  # noqa: S101
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

    def __init__(  # noqa: PLR0913
        self,
        bank_book: BookView,
        view: BRMSTradingBookWidget,
        inspector_ctrl: InspectorController,
        event_bus: EventBus,
        book_type: BookType,
        position_store: PositionStore,
    ) -> None:
        """Initialize the trading book controller."""
        super().__init__(bank_book, view, inspector_ctrl, event_bus, book_type, position_store)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        super().connect_signals()
        assert isinstance(self.bank_book_widget, BRMSTradingBookWidget)  # noqa: S101
        self.bank_book_widget.btn_trading_portfolio_overview.clicked.connect(self.on_btn_trading_portfolio_overview)
        self.bank_book_widget.btn_risk_assessment.clicked.connect(self.on_btn_risk_assessment)
        self.bank_book_widget.btn_mark_to_market_analysis.clicked.connect(self.on_btn_mark_to_market_analysis)
        self.bank_book_widget.btn_trading_profitability.clicked.connect(self.on_btn_trading_profitability)
        self.bank_book_widget.btn_trade_treasury_securities.clicked.connect(self.on_btn_trade_treasury_securities)
        self.bank_book_widget.btn_trade_corporate_securities.clicked.connect(self.on_btn_trade_corporate_securities)
        self.bank_book_widget.btn_trade_derivatives.clicked.connect(self.on_btn_trade_derivatives)

    def on_btn_trading_portfolio_overview(self) -> None:
        """Handle Trading Portfolio Overview button click."""

    def on_btn_risk_assessment(self) -> None:
        """Handle Market Risk Assessment button click."""

    def on_btn_mark_to_market_analysis(self) -> None:
        """Handle Mark-to-Market Analysis button click."""

    def on_btn_trading_profitability(self) -> None:
        """Handle Trading Profitability button click."""

    def on_btn_trade_treasury_securities(self) -> None:
        """Handle Trade Treasury Securities button click."""

    def on_btn_trade_corporate_securities(self) -> None:
        """Handle Trade Corporate Securities button click."""

    def on_btn_trade_derivatives(self) -> None:
        """Handle Trade Derivatives button click."""
