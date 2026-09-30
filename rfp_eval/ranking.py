"""Ranking Tool: deterministic peer ranking.

Mandatory tie-break order (per the project brief):
  1) Higher PPI first
  2) Earlier submission date
  3) Higher historical experience rating
  4) Supplier name in ascending order

Ranks 1, 2, 3, ... are assigned sequentially only after this stable sort,
so the same validated scorecards always produce the same ordering.
"""

from __future__ import annotations

from typing import Any

TIE_BREAK_ORDER: list[str] = [
    "Higher Peer Performance Index (PPI) first",
    "Earlier submission date",
    "Higher historical experience rating",
    "Supplier name in ascending order",
]


def _sort_key(row: dict[str, Any]) -> tuple:
    return (
        -float(row["ppi"]),
        str(row["submission_date"]),
        -float(row["experience_rating"]),
        str(row["supplier_name"]).lower(),
    )


def rank_suppliers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable-sort rows by the mandatory tie-break order and assign final_rank.

    Each input row must carry: supplier_name, submission_date (YYYY-MM-DD),
    experience_rating, ppi. Returns new dicts with ``final_rank`` added.
    """
    ordered = sorted(rows, key=_sort_key)
    ranked: list[dict[str, Any]] = []
    for position, row in enumerate(ordered, start=1):
        new_row = dict(row)
        new_row["final_rank"] = position
        ranked.append(new_row)
    return ranked


def tie_break_explanation() -> str:
    return " > ".join(f"({i}) {step}" for i, step in enumerate(TIE_BREAK_ORDER, start=1))
