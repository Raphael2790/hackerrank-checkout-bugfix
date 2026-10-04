from decimal import Decimal

import pytest

from app.services.payments import InvalidPayment, split_installments


def money_list(*values):
    return [Decimal(v) for v in values]


def test_single_installment():
    assert split_installments(Decimal("125.00"), 1) == money_list("125.00")


def test_even_split():
    assert split_installments(Decimal("100.00"), 4) == money_list("25.00", "25.00", "25.00", "25.00")


def test_uneven_split():
    assert split_installments(Decimal("100.00"), 3) == money_list("33.34", "33.33", "33.33")


@pytest.mark.parametrize("installments", [0, 13, -1])
def test_installments_out_of_range(installments):
    with pytest.raises(InvalidPayment):
        split_installments(Decimal("100.00"), installments)
