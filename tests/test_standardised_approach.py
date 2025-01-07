import pytest

from brms.instruments.base import CreditRating, Instrument, Issuer, IssuerType
from brms.metrics.credit_risk.standardised_approach import RiskWeightTableForSovereignExposures, StandardisedApproach
from brms.models.bank import Bank
from brms.models.base import BookType
from brms.models.scenario import ScenarioManager


class MockInstrument(Instrument):
    def accept(self, visitor, scenario) -> float:
        pass

    @property
    def value(self) -> float:
        return 100  # mock value


def test_compute_sovereign_exposures():
    standardised_approach = StandardisedApproach()
    bank = Bank()
    scenario_manager = ScenarioManager()

    instrument1 = MockInstrument("1", book_type=BookType.BANKING_BOOK)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING_BOOK)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING_BOOK)
    instrument4 = MockInstrument("4", book_type=BookType.BANKING_BOOK)

    instrument1.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.A_PLUS)
    instrument3.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.BB_MINUS)
    instrument4.issuer = Issuer("Firm A", IssuerType.CORPORATE, credit_rating=CreditRating.BB_MINUS)

    bank.assets.add(instrument1)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    expected_rwa = 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument1.issuer.credit_rating)
    assert rwa == expected_rwa

    bank.assets.add(instrument2)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    # fmt: off
    expected_rwa = (
        100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument1.issuer.credit_rating) # 0%
      + 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument2.issuer.credit_rating) # 20%
    )
    # fmt: on
    assert rwa == expected_rwa

    bank.assets.add(instrument3)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    # fmt: off
    expected_rwa = (
        100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument1.issuer.credit_rating) # 0%
      + 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument2.issuer.credit_rating) # 20%
      + 100 * RiskWeightTableForSovereignExposures.get_risk_weight(instrument3.issuer.credit_rating) # 100%
    )
    # fmt: on
    assert rwa == expected_rwa

    # Instrument4 is not issued by sovereigns or central banks. It does not affect RWA for sovereign exposures
    bank.assets.add(instrument4)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


if __name__ == "__main__":
    pytest.main()
