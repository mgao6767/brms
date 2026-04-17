"""Tests for core enums module."""

from brms.core.enums import (
    BookType,
    InstrumentType,
    MeasurementBasis,
    MetricName,
    PositionSide,
    PositionStatus,
    TransactionType,
    ValuationType,
)

EXPECTED_INSTRUMENT_TYPE_COUNT = 17
EXPECTED_BOOK_TYPE_COUNT = 2
EXPECTED_POSITION_SIDE_COUNT = 2
EXPECTED_POSITION_STATUS_COUNT = 2
EXPECTED_MEASUREMENT_BASIS_COUNT = 4
EXPECTED_VALUATION_TYPE_COUNT = 4
EXPECTED_TRANSACTION_TYPE_COUNT = 18
EXPECTED_METRIC_NAME_COUNT = 11


class TestInstrumentType:
    """Tests for InstrumentType enum."""

    def test_instrument_type_members(self) -> None:
        """Test that InstrumentType has all expected members."""
        expected_members = {
            "CASH",
            "DEPOSIT",
            "COMMON_EQUITY",
            "FIXED_RATE_BOND",
            "TREASURY_NOTE",
            "TREASURY_BOND",
            "COVERED_BOND",
            "MORTGAGE",
            "RESIDENTIAL_MORTGAGE",
            "COMMERCIAL_MORTGAGE",
            "AMORTIZING_FIXED_RATE_LOAN",
            "PERSONAL_LOAN",
            "CREDIT_CARD",
            "COMMITMENT",
            "REPURCHASE_AGREEMENT",
            "LETTER_OF_CREDIT",
            "VARIABLE_RATE_LOAN",
        }
        actual_members = {member.name for member in InstrumentType}
        assert actual_members == expected_members  # noqa: S101

    def test_instrument_type_count(self) -> None:
        """Test that InstrumentType has the expected count."""
        assert len(InstrumentType) == EXPECTED_INSTRUMENT_TYPE_COUNT  # noqa: S101


class TestBookType:
    """Tests for BookType enum."""

    def test_book_type_members(self) -> None:
        """Test that BookType has all expected members."""
        expected_members = {"BANKING", "TRADING"}
        actual_members = {member.name for member in BookType}
        assert actual_members == expected_members  # noqa: S101

    def test_book_type_count(self) -> None:
        """Test that BookType has the expected count."""
        assert len(BookType) == EXPECTED_BOOK_TYPE_COUNT  # noqa: S101


class TestPositionSide:
    """Tests for PositionSide enum."""

    def test_position_side_members(self) -> None:
        """Test that PositionSide has all expected members."""
        expected_members = {"LONG", "SHORT"}
        actual_members = {member.name for member in PositionSide}
        assert actual_members == expected_members  # noqa: S101

    def test_position_side_count(self) -> None:
        """Test that PositionSide has the expected count."""
        assert len(PositionSide) == EXPECTED_POSITION_SIDE_COUNT  # noqa: S101


class TestPositionStatus:
    """Tests for PositionStatus enum."""

    def test_position_status_members(self) -> None:
        """Test that PositionStatus has all expected members."""
        expected_members = {"OPEN", "CLOSED"}
        actual_members = {member.name for member in PositionStatus}
        assert actual_members == expected_members  # noqa: S101

    def test_position_status_count(self) -> None:
        """Test that PositionStatus has the expected count."""
        assert len(PositionStatus) == EXPECTED_POSITION_STATUS_COUNT  # noqa: S101


class TestMeasurementBasis:
    """Tests for MeasurementBasis enum."""

    def test_measurement_basis_members(self) -> None:
        """Test that MeasurementBasis has all expected members."""
        expected_members = {"AMORTIZED_COST", "FVOCI", "FVTPL", "NA"}
        actual_members = {member.name for member in MeasurementBasis}
        assert actual_members == expected_members  # noqa: S101

    def test_measurement_basis_count(self) -> None:
        """Test that MeasurementBasis has the expected count."""
        assert len(MeasurementBasis) == EXPECTED_MEASUREMENT_BASIS_COUNT  # noqa: S101


class TestValuationType:
    """Tests for ValuationType enum."""

    def test_valuation_type_members(self) -> None:
        """Test that ValuationType has all expected members."""
        expected_members = {"FAIR_VALUE", "CARRYING_VALUE", "ACCRUED_INTEREST", "NOTIONAL"}
        actual_members = {member.name for member in ValuationType}
        assert actual_members == expected_members  # noqa: S101

    def test_valuation_type_count(self) -> None:
        """Test that ValuationType has the expected count."""
        assert len(ValuationType) == EXPECTED_VALUATION_TYPE_COUNT  # noqa: S101


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_transaction_type_members(self) -> None:
        """Test that TransactionType has all expected members."""
        expected_members = {
            "INTEREST_PAYMENT",
            "MARK_TO_MARKET",
            "MATURITY_SETTLEMENT",
            "COUPON_PAYMENT",
            "LOAN_DISBURSEMENT",
            "LOAN_REPAYMENT",
            "DEPOSIT_RECEIVED",
            "DEPOSIT_WITHDRAWAL",
            "EQUITY_ISSUANCE",
            "SECURITY_PURCHASE",
            "SECURITY_SALE",
            "AMORTIZATION",
            "INTEREST_EXPENSE",
            "PRINCIPAL_PAYMENT",
            "REVALUATION",
            "INTEREST_ACCRUAL",
            "INTEREST_SETTLEMENT",
            "OPENING_BALANCE",
        }
        actual_members = {member.name for member in TransactionType}
        assert actual_members == expected_members  # noqa: S101

    def test_transaction_type_count(self) -> None:
        """Test that TransactionType has the expected count."""
        assert len(TransactionType) == EXPECTED_TRANSACTION_TYPE_COUNT  # noqa: S101


class TestMetricName:
    """Tests for MetricName enum."""

    def test_metric_name_members(self) -> None:
        """Test that MetricName has all expected members."""
        expected_members = {
            "TOTAL_ASSETS",
            "TOTAL_LIABILITIES",
            "TOTAL_EQUITY",
            "CET1_CAPITAL",
            "CET1_RATIO",
            "CREDIT_RWA",
            "OPERATIONAL_RWA",
            "LEVERAGE_RATIO",
            "NET_INTEREST_MARGIN",
            "ROA",
            "ROE",
        }
        actual_members = {member.name for member in MetricName}
        assert actual_members == expected_members  # noqa: S101

    def test_metric_name_count(self) -> None:
        """Test that MetricName has the expected count."""
        assert len(MetricName) == EXPECTED_METRIC_NAME_COUNT  # noqa: S101
