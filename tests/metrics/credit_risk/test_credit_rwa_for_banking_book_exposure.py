import datetime

import pytest

from brms.instruments.base import CreditRating, Instrument, Issuer, IssuerType
from brms.instruments.cash import Cash
from brms.instruments.covered_bond import CoveredBond
from brms.instruments.registry import CorporateInstrumentRegistry
from brms.metrics.credit_risk.internal_ratings_based_approach import InternalRatingsBasedApproach
from brms.metrics.credit_risk.mandate_based_approach import MandateBasedApproach
from brms.metrics.credit_risk.rwa import CreditRWAForBankingBookExposures
from brms.metrics.credit_risk.standardised_approach import StandardisedApproach
from brms.models.bank import Bank
from brms.models.base import BookType
from brms.models.scenario import ScenarioManager


class MockInstrument(Instrument):
    def accept(self, visitor, scenario) -> float:
        pass


class MockCorporateInstrument(MockInstrument):
    pass


CorporateInstrumentRegistry.register(MockCorporateInstrument)


def test_compute_rwa():
    credit_rwa = CreditRWAForBankingBookExposures(StandardisedApproach())
    bank = Bank()
    scenario_manager = ScenarioManager()

    expected_rwa = 0

    # Cash has a risk weight of 0
    cash = Cash("Cash")
    cash.value = 1000
    bank.assets.add(cash)

    # Rated covered bond by a bank with AAA rating, risk weight is 0.1
    instrument1 = CoveredBond("Covered Bond 1", book_type=BookType.BANKING_BOOK, credit_rating=CreditRating.AAA)
    instrument1.issuer = Issuer("Bank 1", IssuerType.BANK)
    instrument1.value = 20000
    bank.assets.add(instrument1)
    expected_rwa += 0.1 * instrument1.value

    # Sovereign exposure by a sovereign with BBB+ rating, risk weight is 0.5
    instrument2 = MockInstrument("Sovereign Bond", book_type=BookType.BANKING_BOOK)
    instrument2.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.BBB_PLUS)
    instrument2.value = 10000
    bank.assets.add(instrument2)
    expected_rwa += 0.5 * instrument2.value

    # Corporate exposure by an unrated firm, risk weight is 1.
    instrument3 = MockCorporateInstrument("C&I loan 1", book_type=BookType.BANKING_BOOK)
    instrument3.issuer = Issuer("Firm 1", IssuerType.CORPORATE, credit_rating=CreditRating.UNRATED)
    instrument3.value = 30000
    bank.assets.add(instrument3)
    expected_rwa += 1.0 * instrument3.value

    today = datetime.date(2025, 1, 1)
    rwa = credit_rwa.compute_rwa(bank, today, scenario_manager)
    assert rwa == expected_rwa


def test_invalid_approach():
    with pytest.raises(TypeError):
        CreditRWAForBankingBookExposures(MandateBasedApproach())


def test_valid_approaches():
    try:
        CreditRWAForBankingBookExposures(StandardisedApproach())
        CreditRWAForBankingBookExposures(InternalRatingsBasedApproach())
    except TypeError:
        pytest.fail("CreditRWAForBankingBookExposures raised TypeError unexpectedly!")


if __name__ == "__main__":
    pytest.main()
