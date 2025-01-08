import pytest

from brms.instruments.base import CreditRating, Instrument, Issuer, IssuerType
from brms.instruments.covered_bond import CoveredBond
from brms.metrics.credit_risk.standardised_approach import (
    RiskWeightTableForCorporateExposures,
    RiskWeightTableForMDBExposures,
    RiskWeightTableForPSEBasedOnExternalRatingOfPSE,
    RiskWeightTableForRatedCoveredBondExposures,
    RiskWeightTableForSovereignExposures,
    StandardisedApproach,
)
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
    risk_table = RiskWeightTableForSovereignExposures

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
    expected_rwa = instrument1.value * risk_table.get_risk_weight(instrument1)
    assert rwa == expected_rwa

    bank.assets.add(instrument2)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
        ],
    )
    assert rwa == expected_rwa

    bank.assets.add(instrument3)
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
    bank.assets.add(instrument4)
    rwa = standardised_approach._compute_sovereign_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


def test_compute_pse_exposures():
    standardised_approach = StandardisedApproach()
    bank = Bank()
    scenario_manager = ScenarioManager()
    risk_table = RiskWeightTableForPSEBasedOnExternalRatingOfPSE

    instrument1 = MockInstrument("1", book_type=BookType.BANKING_BOOK)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING_BOOK)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING_BOOK)
    instrument4 = MockInstrument("4", book_type=BookType.BANKING_BOOK)

    instrument1.issuer = Issuer("PSE", IssuerType.PSE, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("PSE", IssuerType.PSE, credit_rating=CreditRating.A_PLUS)
    instrument3.issuer = Issuer("PSE", IssuerType.PSE, credit_rating=CreditRating.UNRATED)
    instrument4.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)

    bank.assets.add(instrument1)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    expected_rwa = instrument1.value * risk_table.get_risk_weight(instrument1)
    assert rwa == expected_rwa

    bank.assets.add(instrument2)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument1.value * risk_table.get_risk_weight(instrument1),
            instrument2.value * risk_table.get_risk_weight(instrument2),
        ],
    )
    assert rwa == expected_rwa

    bank.assets.add(instrument3)
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
    bank.assets.add(instrument4)
    rwa = standardised_approach._compute_PSE_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


def test_compute_mdb_exposures():
    standardised_approach = StandardisedApproach()
    bank = Bank()
    scenario_manager = ScenarioManager()
    risk_table = RiskWeightTableForMDBExposures

    instrument1 = MockInstrument("1", book_type=BookType.BANKING_BOOK)
    instrument2 = MockInstrument("2", book_type=BookType.BANKING_BOOK)
    instrument3 = MockInstrument("3", book_type=BookType.BANKING_BOOK)
    instrument4 = MockInstrument("4", book_type=BookType.BANKING_BOOK)

    instrument1.issuer = Issuer("Asian Infrastructure Investment Bank", IssuerType.MDB, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("A Random MDB", IssuerType.MDB, credit_rating=CreditRating.A_PLUS)
    instrument3.issuer = Issuer("Another Random MDB", IssuerType.MDB, credit_rating=CreditRating.BBB_PLUS)
    instrument4.issuer = Issuer("Central Bank", IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)

    bank.assets.add(instrument1)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    expected_rwa = 0  # Asian Infrastructure Investment Bank has a 0 risk weight
    assert rwa == expected_rwa

    bank.assets.add(instrument2)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    expected_rwa = instrument2.value * risk_table.get_risk_weight(instrument2)
    assert rwa == expected_rwa

    bank.assets.add(instrument3)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    expected_rwa = sum(
        [
            instrument2.value * risk_table.get_risk_weight(instrument2),
            instrument3.value * risk_table.get_risk_weight(instrument3),
        ],
    )
    assert rwa == expected_rwa

    # Instrument4 is not issued by MDB. It does not affect RWA for PSE exposures.
    bank.assets.add(instrument4)
    rwa = standardised_approach._compute_MDB_exposures(bank, scenario_manager)
    assert rwa == expected_rwa


def test_compute_covered_bond_exposures():
    standardised_approach = StandardisedApproach()
    bank = Bank()
    scenario_manager = ScenarioManager()
    risk_table = RiskWeightTableForRatedCoveredBondExposures

    instrument1 = CoveredBond("Covered Bond 1", book_type=BookType.BANKING_BOOK, credit_rating=CreditRating.AAA)
    instrument2 = CoveredBond("Covered Bond 2", book_type=BookType.BANKING_BOOK, credit_rating=CreditRating.A_PLUS)

    instrument1.issuer = Issuer("Bank 1", IssuerType.BANK)
    instrument2.issuer = Issuer("Bank 2", IssuerType.BANK)

    bank.assets.add(instrument1)
    bank.assets.add(instrument2)

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
    bank = Bank()
    scenario_manager = ScenarioManager()
    risk_table = RiskWeightTableForCorporateExposures

    instrument1 = MockInstrument("C&I loan 1", book_type=BookType.BANKING_BOOK)
    instrument2 = MockInstrument("C&I loan 2", book_type=BookType.BANKING_BOOK)
    instrument3 = MockInstrument("C&I loan 3", book_type=BookType.BANKING_BOOK)

    instrument1.issuer = Issuer("Firm 1", IssuerType.CORPORATE, credit_rating=CreditRating.AAA)
    instrument2.issuer = Issuer("Firm 2", IssuerType.CORPORATE, credit_rating=CreditRating.B_MINUS)
    instrument3.issuer = Issuer("Firm 3", IssuerType.CORPORATE, credit_rating=CreditRating.UNRATED)

    bank.assets.add(instrument1)
    bank.assets.add(instrument2)
    bank.assets.add(instrument3)

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


if __name__ == "__main__":
    pytest.main()
