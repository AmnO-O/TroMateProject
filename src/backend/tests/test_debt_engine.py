from __future__ import annotations

import pytest

from app.services.debt_engine import Transfer, simplify_debts


def _apply(balances: dict[str, int], transfers: list[Transfer[str]]) -> dict[str, int]:
    after = dict(balances)
    for t in transfers:
        after[t.debtor] += t.amount
        after[t.creditor] -= t.amount
    return after


def test_payer_is_paid_back_by_everyone_who_owes() -> None:
    transfers = simplify_debts({"Hao": 200_000, "Lan": -100_000, "Minh": -100_000})
    assert transfers == [
        Transfer("Lan", "Hao", 100_000),
        Transfer("Minh", "Hao", 100_000),
    ]


def test_largest_debtor_settles_with_largest_creditor_first() -> None:
    balances = {"A": 50_000, "B": 150_000, "C": -120_000, "D": -80_000}
    transfers = simplify_debts(balances)
    assert transfers[0] == Transfer("C", "B", 120_000)
    assert all(v == 0 for v in _apply(balances, transfers).values())
    assert len(transfers) <= len(balances) - 1


@pytest.mark.parametrize(
    "balances",
    [
        {},
        {"A": 0, "B": 0},
        {"A": 1, "B": -1},
        {"A": 70_000, "B": -10_000, "C": -20_000, "D": -40_000},
        {"A": 33_334, "B": -16_667, "C": -16_667, "D": 0},
    ],
)
def test_transfers_clear_every_balance_with_at_most_n_minus_1_steps(balances) -> None:
    transfers = simplify_debts(balances)
    assert all(v == 0 for v in _apply(balances, transfers).values())
    assert all(t.amount > 0 for t in transfers)
    non_zero = sum(1 for v in balances.values() if v)
    assert len(transfers) <= max(non_zero - 1, 0)


def test_ties_follow_input_order_so_output_is_stable() -> None:
    balances = {"A": 10, "B": 10, "C": -10, "D": -10}
    assert simplify_debts(balances) == simplify_debts(dict(balances))
    assert simplify_debts(balances) == [Transfer("C", "A", 10), Transfer("D", "B", 10)]
