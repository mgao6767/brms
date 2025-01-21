"""Main controller module for the BRMS application."""

from brms.controllers.bank_controller import BankController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class MainController(BRMSController):
    """Main controller class for handling the interaction between the model and view."""

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        self.simulation: SimulationModel = model
        self.view: MainWindow = view
        # Sub controllers
        self.inspector_ctrl = InspectorController(inspector_widget=self.view.inspector_widget)
        self.bank_ctrl = BankController(
            bank=self.simulation.bank,
            banking_book_view=self.view.banking_book_widget,
            trading_book_view=self.view.trading_book_widget,
            inspector_ctrl=self.inspector_ctrl,
        )
        # Connect signals
        self.connect_signals()
        self._test()

    def connect_signals(self) -> None:
        """Connect signals from the view to the controller's slots."""
        self.view.exit_signal.connect(self.handle_exit)

    def handle_exit(self) -> None:
        """Handle the exit signal from the view."""
        # Perform any cleanup or save operations here
        self.view.close()

    def _test(self) -> None:
        import QuantLib as ql
        from brms.instruments.mock import MockInstrument
        from brms.models.bank_book import Position
        from brms.models.base import BookType
        from brms.instruments.base import BookType, CreditRating, Issuer, IssuerType
        from brms.instruments.fixed_rate_bond import FixedRateBond

        for i in range(100):
            instrument_name = f"mock_instrument_{i}"
            self.bank_ctrl.add_instrument_to_banking_book(MockInstrument(instrument_name), position=Position.LONG)
            self.bank_ctrl.add_instrument_to_banking_book(MockInstrument(instrument_name), position=Position.SHORT)

        for i in range(100):
            instrument_name = f"mock_instrument_{i}"
            inst = MockInstrument(instrument_name, book_type=BookType.TRADING_BOOK)
            inst.value = i * 100
            self.bank_ctrl.add_instrument_to_trading_book(inst, position=Position.LONG)

        face_value = 1000.0
        coupon_rate = 0.05
        issue_date = ql.Date(1, 1, 2020)
        maturity_date = ql.Date(1, 1, 2030)
        bond = FixedRateBond(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date,
            maturity_date=maturity_date,
            book_type=BookType.TRADING_BOOK,
            credit_rating=CreditRating.AA_MINUS,
            issuer=Issuer(
                name="Asian Development Bank",
                issuer_type=IssuerType.MDB,
                credit_rating=CreditRating.AA,
            ),
        )

        self.bank_ctrl.add_instrument_to_banking_book(bond, position=Position.LONG)
