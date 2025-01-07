import pytest

from brms.instruments.base import CreditRating, Instrument
from brms.metrics.credit_risk.standardised_approach import RiskWeightTableForSovereignExposures, StandardisedApproach
from brms.models.bank import Bank
from brms.models.base import BookType
from brms.models.scenario import ScenarioManager


class MockInstrument(Instrument):
    def __init__(self, name: str, book_type: BookType, value: float, credit_rating: CreditRating):
        super().__init__(name)
        self.book_type = book_type
        self.value = value
        self.credit_rating = credit_rating

    def accept(self, visitor, scenario) -> float:
        pass


def test_compute_sovereign_exposures():
    standardised_approach = StandardisedApproach()
    bank = Bank()
    scenario_manager = ScenarioManager()

    instrument1 = MockInstrument("1", book_type=BookType.BANKING_BOOK, value=100, credit_rating=CreditRating.AAA)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING_BOOK, value=100, credit_rating=CreditRating.A_PLUS)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING_BOOK, value=100, credit_rating=CreditRating.BB_MINUS)

    bank.assets.add(instrument1)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    expected_rwa = 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument1.credit_rating)
    assert rwa == expected_rwa

    bank.assets.add(instrument2)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    # fmt: off
    expected_rwa = (
        100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument1.credit_rating) # 0%
      + 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument2.credit_rating) # 20%
    )
    # fmt: on
    assert rwa == expected_rwa

    bank.assets.add(instrument3)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    # fmt: off
    expected_rwa = (
        100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument1.credit_rating) # 0%
      + 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument2.credit_rating) # 20%
      + 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument3.credit_rating) # 100%
    )
    # fmt: on
    assert rwa == expected_rwa


if __name__ == "__main__":
    pytest.main()
