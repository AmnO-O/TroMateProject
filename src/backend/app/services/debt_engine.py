"""DebtEngine: turn net room balances into a short list of suggested transfers.

Pure functions only (no database, no Telegram), so the rules can be unit-tested in isolation.

Sign convention matches ``LedgerEntry.amount_delta``: a positive balance means the room owes
the member (they should receive money), a negative balance means the member owes the room.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Transfer[K: Hashable]:
    """``debtor`` pays ``creditor`` ``amount`` whole VND."""

    debtor: K
    creditor: K
    amount: int


def simplify_debts[K: Hashable](balances: Mapping[K, int]) -> list[Transfer[K]]:
    """Greedy minimum cash flow: settle the largest debtor against the largest creditor.

    Every step clears at least one member, so ``n`` members with a non-zero balance need at
    most ``n - 1`` transfers. Ties are broken by the order of ``balances`` so the same input
    always yields the same suggestion. Balances are expected to sum to zero (the ledger is
    double-entry); if they do not, the unmatched remainder is simply left out.
    """

    order = {key: index for index, key in enumerate(balances)}
    debtors = [[-amount, key] for key, amount in balances.items() if amount < 0]
    creditors = [[amount, key] for key, amount in balances.items() if amount > 0]

    def largest_first(entry: list) -> tuple[int, int]:
        return -entry[0], order[entry[1]]

    transfers: list[Transfer[K]] = []
    while debtors and creditors:
        debtors.sort(key=largest_first)
        creditors.sort(key=largest_first)
        debtor, creditor = debtors[0], creditors[0]
        amount = min(debtor[0], creditor[0])
        transfers.append(Transfer(debtor=debtor[1], creditor=creditor[1], amount=amount))
        debtor[0] -= amount
        creditor[0] -= amount
        if debtor[0] == 0:
            debtors.pop(0)
        if creditor[0] == 0:
            creditors.pop(0)
    return transfers
