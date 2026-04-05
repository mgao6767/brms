import datetime

import pytest

from brms.core.metrics.risk.credit_risk.standardised_approach import (
    RiskWeightTableForCorporateExposures,
    RiskWeightTableForMDBExposures,
    RiskWeightTableForPSEBasedOnExternalRatingOfPSE,
    RiskWeightTableForRatedCoveredBondExposures,
    RiskWeightTableForSovereignExposures,
    StandardisedApproach,
)
from brms.core.models.instruments.base import BookType, CreditRating, Instrument, Issuer, IssuerType
from brms.core.models.instruments.bonds import CoveredBond
from brms.core.models.instruments.deposits import Cash
from brms.core.models.instruments.registry import CorporateInstrumentRegistry


class _MockBank:
    """Minimal mock with a banking_book_assets() iterable."""

    def __init__(self) -> None:
        self._assets: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        self._assets.append(instrument)

    def banking_book_assets(self):
        return iter(self._assets)


class MockInstrument(Instrument):
    def __init__(self, name, book_type=None, credit_rating=None, issuer=None, parent=None):
        super().__init__(name, book_type, credit_rating, issuer, parent)
        self.value = 100  # mock value

    def accept(self, visitor) -> None:
        pass


class MockCorporateInstrument(MockInstrument):
    pass


CorporateInstrumentRegistry.register(MockCorporateInstrument)


def test_compute_sovereign_exposures():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None
    risk_table = RiskWeightTableForSovereignExposures

    instrument1 = MockInstrument("1", book_type=BookType.BANKING)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING)
    instrument4 = MockInstrument("4", book_type=BookType.BANKING)

    instrument1.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.A_PLUS)
    instrument3.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.BB_MINUS)
    instrument4.issuer = Issuer("Firm A", IssuerType.CORPORATE, credit_rating=CreditRating.BB_MINUS)

    bank.add(instrument1)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    expected_rwa = instrument1.value * risk_table.get_risk_weight(instrument1)
    assert rwa == expected_rwa

    bank.add(instrument2)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
        ],
    )
    assert rwa == expected_rwa

    bank.add(instrument3)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
            instrument3.value * risk_table.get_risk_weight(instrument3),
        ],
    )
    assert rwa == expected_rwa

    # Instrument4 is not issued by sovereigns or central banks. It does not affect RWA for sovereign exposures
    bank.add(instrument4)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


def test_compute_pse_exposures():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None
    risk_table = RiskWeightTableForPSEBasedOnExternalRatingOfPSE

    instrument1 = MockInstrument("1", book_type=BookType.BANKING)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING)
    instrument4 = MockInstrument("4", book_type=BookType.BANKING)

    instrument1.issuer = Issuer("PSE", IssuerType.PSE, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("PSE", IssuerType.PSE, credit_rating=CreditRating.A_PLUS)
    instrument3.issuer = Issuer("PSE", IssuerType.PSE, credit_rating=CreditRating.UNRATED)
    instrument4.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)

    bank.add(instrument1)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    expected_rwa = instrument1.value * risk_table.get_risk_weight(instrument1)
    assert rwa == expected_rwa

    bank.add(instrument2)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
        ],
    )
    assert rwa == expected_rwa

    bank.add(instrument3)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
            instrument3.value * risk_table.get_risk_weight(instrument3),
        ],
    )
    assert rwa == expected_rwa

    # Instrument4 is not issued by PSE. It does not affect RWA for PSE exposures.
    bank.add(instrument4)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


def test_compute_mdb_exposures():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None
    risk_table = RiskWeightTableForMDBExposures

    instrument1 = MockInstrument("1", book_type=BookType.BANKING)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING)
    instrument4 = MockInstrument("4", book_type=BookType.BANKING)

    instrument1.issuer = Issuer("Asian Infrastructure Investment Bank", IssuerType.MDB, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("A Random MDB", IssuerType.MDB, credit_rating=CreditRating.A_PLUS)
    instrument3.issuer = Issuer("Another Random MDB", IssuerType.MDB, credit_rating=CreditRating.BBB_PLUS)
    instrument4.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)

    bank.add(instrument1)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    expected_rwa = 0  # Asian Infrastructure Investment Bank has a 0 risk weight
    assert rwa == expected_rwa

    bank.add(instrument2)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    expected_rwa = instrument2.value * risk_table.get_risk_weight(instrument2)
    assert rwa == expected_rwa

    bank.add(instrument3)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument2.value * risk_table.get_risk_weight(instrument2),
            instrument3.value * risk_table.get_risk_weight(instrument3),
        ],
    )
    assert rwa == expected_rwa

    # Instrument4 is not issued by MDB. It does not affect RWA for PSE exposures.
    bank.add(instrument4)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


def test_compute_covered_bond_exposures():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None
    risk_table = RiskWeightTableForRatedCoveredBondExposures

    instrument1 = CoveredBond("Covered Bond 1", book_type=BookType.BANKING, credit_rating=CreditRating.AAA)
    instrument2 = CoveredBond("Covered Bond 2", book_type=BookType.BANKING, credit_rating=CreditRating.A_PLUS)

    instrument1.issuer = Issuer("Bank 1", IssuerType.BANK)
    instrument2.issuer = Issuer("Bank 2", IssuerType.BANK)

    bank.add(instrument1)
    bank.add(instrument2)

    rwa = standardised_approach._compute_covered_bonds_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
        ],
    )
    assert rwa == expected_rwa


def test_compute_corporate_exposures():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None
    risk_table = RiskWeightTableForCorporateExposures

    instrument1 = MockCorporateInstrument("C&I loan 1", book_type=BookType.BANKING)
    instrument2 = MockCorporateInstrument("C&I loan 2", book_type=BookType.BANKING)
    instrument3 = MockCorporateInstrument("C&I loan 3", book_type=BookType.BANKING)

    instrument1.issuer = Issuer("Firm 1", IssuerType.CORPORATE, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("Firm 2", IssuerType.CORPORATE, credit_rating=CreditRating.B_MINUS)
    instrument3.issuer = Issuer("Firm 3", IssuerType.CORPORATE, credit_rating=CreditRating.UNRATED)

    bank.add(instrument1)
    bank.add(instrument2)
    bank.add(instrument3)

    rwa = standardised_approach._compute_corporate_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
            instrument3.value * risk_table.get_risk_weight(instrument3),
        ],
    )
    assert rwa == expected_rwa


@pytest.mark.skip("Not yet implemented")
def test_compute_retail_exposures():
    pass


@pytest.mark.skip("Not yet implemented")
def test_compute_real_estate_exposures():
    pass


def test_compute_other_exposures():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None

    cash = Cash(1000)
    bank.add(cash)

    rwa = standardised_approach._compute_other_assets_exposures(bank, scenario_manager)
    expected_rwa = 0
    assert rwa == expected_rwa

    # Adding other assets should have no effect
    instrument1 = CoveredBond("Covered Bond 1", book_type=BookType.BANKING, credit_rating=CreditRating.AAA)
    instrument1.issuer = Issuer("Bank 1", IssuerType.BANK)
    bank.add(instrument1)

    rwa = standardised_approach._compute_other_assets_exposures(bank, scenario_manager)
    expected_rwa = 0
    assert rwa == expected_rwa


def test_compute_rwa():
    standardised_approach = StandardisedApproach()
    bank = _MockBank()
    scenario_manager = None

    today = datetime.date(2025, 1, 1)
    expected_rwa = 0

    # Cash has a risk weight of 0
    cash = Cash(1000)
    bank.add(cash)
    rwa = standardised_approach.compute_rwa(bank, today, scenario_manager)
    assert rwa == expected_rwa

    # Rated covered bond by a bank with AAA rating, risk weight is 0.1
    instrument1 = CoveredBond("Covered Bond 1", book_type=BookType.BANKING, credit_rating=CreditRating.AAA)
    instrument1.issuer = Issuer("Bank 1", IssuerType.BANK)
    instrument1.value = 20000
    bank.add(instrument1)
    rwa = standardised_approach.compute_rwa(bank, today, scenario_manager)
    expected_rwa += 0.1 * instrument1.value
    assert rwa == expected_rwa

    # Sovereign exposure by a sovereign with BBB+ rating, risk weight is 0.5
    instrument2 = MockInstrument("Sovereign Bond", book_type=BookType.BANKING)
    instrument2.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.BBB_PLUS)
    instrument2.value = 10000
    bank.add(instrument2)
    rwa = standardised_approach.compute_rwa(bank, today, scenario_manager)
    expected_rwa += 0.5 * instrument2.value
    assert rwa == expected_rwa

    # Corporate exposure by an unrated firm, risk weight is 1.
    instrument3 = MockCorporateInstrument("C&I loan 1", book_type=BookType.BANKING)
    instrument3.issuer = Issuer("Firm 1", IssuerType.CORPORATE, credit_rating=CreditRating.UNRATED)
    instrument3.value = 30000
    bank.add(instrument3)
    rwa = standardised_approach.compute_rwa(bank, today, scenario_manager)
    expected_rwa += 1.0 * instrument3.value
    assert rwa == expected_rwa


if __name__ == "__main__":
    pytest.main([__file__])
