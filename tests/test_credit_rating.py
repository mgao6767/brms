import pytest

from brms.instruments.base import CreditRating


def test_credit_rating_comparison():
    """Test the comparison operators for CreditRating."""
    assert CreditRating.AAA > CreditRating.AA_PLUS
    assert CreditRating.AA_PLUS > CreditRating.AA
    assert CreditRating.AA == CreditRating.AA
    assert CreditRating.BBB < CreditRating.A
    assert CreditRating.BBB_PLUS <= CreditRating.BBB_PLUS
    assert CreditRating.BBB_MINUS >= CreditRating.BBB_MINUS
    assert CreditRating.CCC < CreditRating.BBB
    assert CreditRating.D < CreditRating.CCC
    assert CreditRating.AAA >= CreditRating.AAA >= CreditRating.AA_PLUS
    assert CreditRating.AAA >= CreditRating.AA_PLUS > CreditRating.A_PLUS
    assert CreditRating.BBB >= CreditRating.BBB >= CreditRating.BBB


def test_credit_rating_investment_grade():
    """Test the is_investment_grade method."""
    assert CreditRating.AAA.is_investment_grade() is True
    assert CreditRating.A.is_investment_grade() is True
    assert CreditRating.BBB.is_investment_grade() is True
    assert CreditRating.BBB_MINUS.is_investment_grade() is True
    assert CreditRating.BB_PLUS.is_investment_grade() is False
    assert CreditRating.B.is_investment_grade() is False
    assert CreditRating.CCC.is_investment_grade() is False
    assert CreditRating.D.is_investment_grade() is False


def test_credit_rating_enum_values():
    """Test the enum values of CreditRating."""
    assert CreditRating.AAA.value == 1
    assert CreditRating.AA_PLUS.value == 2
    assert CreditRating.AA.value == 3
    assert CreditRating.AA_MINUS.value == 4
    assert CreditRating.A_PLUS.value == 5
    assert CreditRating.A.value == 6
    assert CreditRating.A_MINUS.value == 7
    assert CreditRating.BBB_PLUS.value == 8
    assert CreditRating.BBB.value == 9
    assert CreditRating.BBB_MINUS.value == 10
    assert CreditRating.BB_PLUS.value == 11
    assert CreditRating.BB.value == 12
    assert CreditRating.BB_MINUS.value == 13
    assert CreditRating.B_PLUS.value == 14
    assert CreditRating.B.value == 15
    assert CreditRating.B_MINUS.value == 16
    assert CreditRating.CCC_PLUS.value == 17
    assert CreditRating.CCC.value == 18
    assert CreditRating.CCC_MINUS.value == 19
    assert CreditRating.CC.value == 20
    assert CreditRating.C.value == 21
    assert CreditRating.D.value == 22
    assert CreditRating.UNRATED.value == 23


if __name__ == "__main__":
    pytest.main()
