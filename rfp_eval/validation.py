"""Validation Tool: checks the LLM scorecard schema, normalizes problems,
and records warnings instead of failing silently.

Normalization policy:
- Missing criterion            -> filled with score 0, flagged ``imputed=True``
- Score out of [0, max_score]  -> clipped into range, flagged ``clipped=True``
- Non-numeric score            -> coerced when possible, else 0
- max_score mismatch           -> the database value wins
- Unknown / duplicate criterion ids -> ignored (first wins), warning recorded
- Missing justification/evidence/risks/summary -> defaulted, warning recorded
"""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """Raised when the LLM output is structurally unusable."""


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def validate_llm_output(
    raw: Any,
    criteria: list[dict[str, Any]],
    supplier_name: str,
) -> tuple[dict[str, Any], list[str]]:
    """Validate + normalize one supplier scorecard.

    Returns:
        (normalized_scorecard, warnings)
    Raises:
        ValidationError: if ``raw`` is not a dict or has no usable criteria list.
    """
    warnings: list[str] = []

    if not isinstance(raw, dict):
        raise ValidationError(f"LLM output for '{supplier_name}' is not a JSON object.")
    raw_criteria = raw.get("criteria")
    if not isinstance(raw_criteria, list):
        raise ValidationError(
            f"LLM output for '{supplier_name}' is missing the 'criteria' list."
        )

    # Index LLM entries by criterion_id (first occurrence wins).
    by_id: dict[int, dict[str, Any]] = {}
    for entry in raw_criteria:
        if not isinstance(entry, dict):
            warnings.append(f"Ignored a non-object entry in 'criteria' for '{supplier_name}'.")
            continue
        cid = _coerce_float(entry.get("criterion_id"))
        if cid is None:
            warnings.append(f"Ignored a criterion entry with invalid id for '{supplier_name}'.")
            continue
        cid = int(cid)
        if cid in by_id:
            warnings.append(
                f"Duplicate result for criterion {cid} for '{supplier_name}'; kept the first."
            )
            continue
        by_id[cid] = entry

    known_ids = {int(c["criterion_id"]) for c in criteria}
    for cid in sorted(set(by_id) - known_ids):
        warnings.append(
            f"Ignored result for unknown criterion_id {cid} for '{supplier_name}'."
        )

    name = raw.get("supplier_name") or supplier_name
    if name != supplier_name:
        warnings.append(
            f"LLM returned supplier_name '{name}' but the evaluated supplier is "
            f"'{supplier_name}'; using the latter."
        )

    normalized_criteria: list[dict[str, Any]] = []
    for c in criteria:
        cid = int(c["criterion_id"])
        max_score = float(c["max_score"])
        entry = by_id.get(cid)

        if entry is None:
            warnings.append(
                f"Missing result for criterion '{c['name']}' (id {cid}) for "
                f"'{supplier_name}'; imputed score 0."
            )
            normalized_criteria.append(
                {
                    "criterion_id": cid,
                    "name": c["name"],
                    "score": 0.0,
                    "max_score": max_score,
                    "justification": "No result returned by the model; score imputed as 0.",
                    "evidence": "",
                    "imputed": True,
                    "clipped": False,
                }
            )
            continue

        score = _coerce_float(entry.get("score"))
        if score is None:
            warnings.append(
                f"Unparseable score for '{c['name']}' for '{supplier_name}'; set to 0."
            )
            score = 0.0
        clipped = False
        if score < 0 or score > max_score:
            warnings.append(
                f"Score {score:g} for '{c['name']}' for '{supplier_name}' outside "
                f"[0, {max_score:g}]; clipped."
            )
            score = max(0.0, min(max_score, score))
            clipped = True

        entry_max = _coerce_float(entry.get("max_score"))
        if entry_max is None or entry_max != max_score:
            warnings.append(
                f"max_score mismatch for '{c['name']}' for '{supplier_name}' "
                f"(got {entry.get('max_score')!r}); using database value {max_score:g}."
            )

        justification = entry.get("justification") or ""
        evidence = entry.get("evidence") or ""
        if not justification:
            warnings.append(f"Missing justification for '{c['name']}' for '{supplier_name}'.")
        if not evidence:
            warnings.append(f"Missing evidence for '{c['name']}' for '{supplier_name}'.")

        normalized_criteria.append(
            {
                "criterion_id": cid,
                "name": c["name"],
                "score": round(score, 2),
                "max_score": max_score,
                "justification": str(justification),
                "evidence": str(evidence),
                "imputed": False,
                "clipped": clipped,
            }
        )

    risks = raw.get("risks") or []
    if not isinstance(risks, list):
        warnings.append(f"'risks' was not a list for '{supplier_name}'; reset to empty.")
        risks = []
    risks = [str(r) for r in risks]

    summary = raw.get("overall_summary") or ""
    if not summary:
        warnings.append(f"Missing overall_summary for '{supplier_name}'.")

    normalized = {
        "supplier_name": supplier_name,
        "criteria": normalized_criteria,
        "risks": risks,
        "overall_summary": str(summary),
    }
    return normalized, warnings
