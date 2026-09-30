"""Deterministic scoring math (the LLM never touches these).

Formulas (per the project brief):
- Absolute weighted score = SUM over criteria of (score / max_score) * weight   (0..100)
- Criterion benchmark     = highest valid score observed for that criterion
- Criterion gap           = supplier score - benchmark  (0 for the leader, else negative)
- Relative performance %  = (supplier score / benchmark) * 100
                            (100.0 for everyone if the benchmark is 0)
- Peer Performance Index  = weighted average of the relative-performance percentages
"""

from __future__ import annotations

from typing import Any


def absolute_weighted_score(
    criterion_scores: dict[int, float],
    criteria: list[dict[str, Any]],
) -> float:
    """SUM (score / max_score) * weight over active criteria. Scale: 0..100."""
    total = 0.0
    for c in criteria:
        cid = int(c["criterion_id"])
        max_score = float(c["max_score"])
        score = float(criterion_scores.get(cid, 0.0))
        ratio = (score / max_score) if max_score > 0 else 0.0
        total += ratio * float(c["weight"])
    return round(total, 2)


def compute_benchmarks(
    all_scores: list[dict[int, float]],
    criteria: list[dict[str, Any]],
) -> dict[int, float]:
    """Highest observed score per criterion across all suppliers."""
    benchmarks: dict[int, float] = {}
    for c in criteria:
        cid = int(c["criterion_id"])
        benchmarks[cid] = round(max((s.get(cid, 0.0) for s in all_scores), default=0.0), 2)
    return benchmarks


def criterion_gap(score: float, benchmark: float) -> float:
    return round(score - benchmark, 2)


def relative_performance_pct(score: float, benchmark: float) -> float:
    """(score / benchmark) * 100 with safe handling when benchmark is 0."""
    if benchmark <= 0:
        return 100.0  # every supplier scored 0 -> all equal to the benchmark
    return round(score / benchmark * 100, 2)


def peer_performance_index(
    relative_pcts: dict[int, float],
    criteria: list[dict[str, Any]],
) -> float:
    """Weighted average of criterion relative-performance percentages. Scale: 0..100."""
    total_weight = sum(float(c["weight"]) for c in criteria)
    if total_weight <= 0:
        return 0.0
    weighted = sum(
        relative_pcts.get(int(c["criterion_id"]), 0.0) * float(c["weight"])
        for c in criteria
    )
    return round(weighted / total_weight, 2)
