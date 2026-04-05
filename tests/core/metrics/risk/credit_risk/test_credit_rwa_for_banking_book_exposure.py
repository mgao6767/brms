import datetime

import pytest

from brms.core.metrics.risk.credit_risk.internal_ratings_based_approach import InternalRatingsBasedApproach
from brms.core.metrics.risk.credit_risk.mandate_based_approach import MandateBasedApproach
from brms.core.metrics.risk.credit_risk.rwa import CreditRWAForBankingBookExposures
from brms.core.metrics.risk.credit_risk.standardised_approach import StandardisedApproach
from brms.core.models.instruments.base import BookType, CreditRating, Instrument, Issuer, IssuerType
from brms.core.models.instruments.bonds import CoveredBond
from brms.core.models.instruments.deposits import Cash
from brms.core.models.instruments.registry import CorporateInstrumentRegistry


class MockInstrument(Instrument):
    def accept(self, visitor) -> None:
        pass


class MockCorporateInstrument(MockInstrument):
    pass


CorporateInstrumentRegistry.register(MockCorporateInstrument)


class _MockBank:
    """Minimal mock with a banking_book_assets() iterable."""

    def __init__(self) -> None:
        self._assets: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        self._assets.append(instrument)

    def banking_book_assets(self):
        return iter(self._assets)


def test_compute_rwa():
    credit_rwa = CreditRWAForBankingBookExposures(StandardisedApproach())
    bank = _MockBank()
    scenario_manager = None

    expected_rwa = 0

    # Cash has a risk weight of 0
    cash = Cash()
    cash.value = 1000
    bank.add(cash)

    # Rated covered bond by a bank with AAA rating, risk weight is 0.1
    instrument1 = CoveredBond(name="Covered Bond 1", book_type=BookType.BANKING, credit_rating=CreditRating.AAA)
    instrument1.issuer = Issuer("Bank 1", IssuerType.BANK)
    instrument1.value = 20000
    bank.add(instrument1)
    expected_rwa += 0.1 * instrument1.value

    # Sovereign exposure by a sovereign with BBB+ rating, risk weight is 0.5
    instrument2 = MockInstrument("Sovereign Bond", book_type=BookType.BANKING)
    instrument2.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.BBB_PLUS)
    instrument2.value = 10000
    bank.add(instrument2)
    expected_rwa += 0.5 * instrument2.value

    # Corporate exposure by an unrated firm, risk weight is 1.
    instrument3 = MockCorporateInstrument("C&I loan 1", book_type=BookType.BANKING)
    instrument3.issuer = Issuer("Firm 1", IssuerType.CORPORATE, credit_rating=CreditRating.UNRATED)
    instrument3.value = 30000
    bank.add(instrument3)
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
    pytest.main([__file__])
