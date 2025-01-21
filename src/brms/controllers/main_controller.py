"""Main controller module for the BRMS application."""

from brms.controllers.bank_controller import BankController
from brms.controllers.base import BRMSController
from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class MainController(BRMSController):
    """Main controller class for handling the interaction between the model and view."""

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        self.simulation: SimulationModel = model
        self.view: MainWindow = view
        # Sub controllers
        self.bank_ctrl = BankController(
            bank=self.simulation.bank,
            banking_book_view=self.view.banking_book_widget,
            trading_book_view=self.view.trading_book_widget,
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
        from brms.instruments.mock import MockInstrument
        from brms.models.bank_book import Position

        for i in range(100):
            instrument_name = f"mock_instrument_{i}"
            self.bank_ctrl.add_instrument_to_banking_book(MockInstrument(instrument_name), position=Position.LONG)
            self.bank_ctrl.add_instrument_to_banking_book(MockInstrument(instrument_name), position=Position.SHORT)
            inst = MockInstrument(instrument_name)
            inst.value = i * 100
            self.bank_ctrl.add_instrument_to_trading_book(inst, position=Position.LONG)
            self.bank_ctrl.remove_instrument_from_trading_book(inst, position=Position.LONG)
            self.bank_ctrl.add_instrument_to_trading_book(MockInstrument(instrument_name), position=Position.SHORT)
