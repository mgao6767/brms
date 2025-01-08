"""Module defining classes for calculating Credit Risk Weighted Assets (RWA)."""

import datetime

from brms.metrics.base import RWAApproach, RWAComponent
from brms.metrics.credit_risk import (
    CentralCounterpartyRiskDefaultApproach, CounterpartyRiskDefaultApproach,
    FallBackApproach, InternalAssessmentApproach, InternalRatingsBasedApproach,
    LookThroughApproach, MandateBasedApproach,
    SecuritisationExternalRatingsBasedApproach,
    SecuritisationInternalRatingsBasedApproach,
    SecuritisationStandardisedApproach, StandardisedApproach,
    UnsettledTransactionsFailedTradesDefaultApproach)
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class CreditRWAForBankingBookExposures(RWAComponent):
    """Credit RWA for banking book exposures."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Credit Risk."""
        return [StandardisedApproach, InternalRatingsBasedApproach]


class CreditRWACounterpartyCreditRisk(RWAComponent):
    """RWA for counterparty credit risk arising from banking book exposures and from trading book instruments."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Credit Risk."""
        return [CounterpartyRiskDefaultApproach]


class CreditRWAForEquityInvestmentsInFunds(RWAComponent):
    """Credit RWA for equity investments in funds that are held in the banking book."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Credit Risk."""
        return [LookThroughApproach, MandateBasedApproach, FallBackApproach]


class CreditRWASecuritisationExposures(RWAComponent):
    """RWA for securitisation exposures held in the banking book."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Credit Risk."""
        return [
            SecuritisationStandardisedApproach,
            SecuritisationExternalRatingsBasedApproach,
            InternalAssessmentApproach,
            SecuritisationInternalRatingsBasedApproach,
        ]


class CreditRWAExposuresToCentralCounterparties(RWAComponent):
    """RWA for exposures to central counterparties in the banking book and trading book."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Credit Risk."""
        return [CentralCounterpartyRiskDefaultApproach]


class CreditRWAUnsettledTransactionsFailedTrades(RWAComponent):
    """RWA for the risk posed by unsettled transactions and failed trades."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Credit Risk."""
        return [UnsettledTransactionsFailedTradesDefaultApproach]


class RWACreditRisk:
    """Class for calculating Credit Risk Weighted Assets (RWA) for various exposure types."""

    def __init__(self) -> None:
        """Initialize the RWACreditRisk class."""
        self.rwa_banking_book_exposures = CreditRWAForBankingBookExposures()
        self.rwa_counterparty_credit_risk = CreditRWACounterpartyCreditRisk()
        self.rwa_equity_investments_in_funds = CreditRWAForEquityInvestmentsInFunds()
        self.rwa_securitisation_exposures = CreditRWASecuritisationExposures()
        self.rwa_exposures_to_central_counterparties = CreditRWAExposuresToCentralCounterparties()
        self.rwa_unsettled_transactions_failed_trades = CreditRWAUnsettledTransactionsFailedTrades()

        self._rwa_components: list[RWAComponent] = [
            self.rwa_banking_book_exposures,
            self.rwa_counterparty_credit_risk,
            self.rwa_equity_investments_in_funds,
            self.rwa_securitisation_exposures,
            self.rwa_exposures_to_central_counterparties,
            self.rwa_unsettled_transactions_failed_trades,
        ]

        self.set_approach_for_banking_book_exposures(StandardisedApproach())
        self.set_approach_for_counterparty_credit_risk(CounterpartyRiskDefaultApproach())
        self.set_approach_for_equity_investments_in_funds(LookThroughApproach())
        self.set_approach_for_securitisation_exposures(SecuritisationStandardisedApproach())
        self.set_approach_for_exposures_to_central_counterparties(CentralCounterpartyRiskDefaultApproach())
        self.set_approach_for_unsettled_transactions_failed_trades(UnsettledTransactionsFailedTradesDefaultApproach())

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the total Credit RWA for the bank under the given scenario."""
        return sum(component.compute_rwa(bank, date, scenario_manager) for component in self._rwa_components)

    def set_approach_for_banking_book_exposures(self, approach: RWAApproach) -> None:
        """Set the approach for banking book exposures."""
        self.rwa_banking_book_exposures.approach = approach

    def set_approach_for_counterparty_credit_risk(self, approach: RWAApproach) -> None:
        """Set the approach for counterparty credit risk."""
        self.rwa_counterparty_credit_risk.approach = approach

    def set_approach_for_equity_investments_in_funds(self, approach: RWAApproach) -> None:
        """Set the approach for equity investments in funds."""
        self.rwa_equity_investments_in_funds.approach = approach

    def set_approach_for_securitisation_exposures(self, approach: RWAApproach) -> None:
        """Set the approach for securitisation exposures."""
        self.rwa_securitisation_exposures.approach = approach

    def set_approach_for_exposures_to_central_counterparties(self, approach: RWAApproach) -> None:
        """Set the approach for exposures to central counterparties."""
        self.rwa_exposures_to_central_counterparties.approach = approach

    def set_approach_for_unsettled_transactions_failed_trades(self, approach: RWAApproach) -> None:
        """Set the approach for unsettled transactions and failed trades."""
        self.rwa_unsettled_transactions_failed_trades.approach = approach
