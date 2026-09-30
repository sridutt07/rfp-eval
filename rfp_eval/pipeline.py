"""Orchestrator Agent: controls the end-to-end evaluation workflow.

Data flow (mirrors section 4 of the brief):
  1. Setup      load active criteria from SQLite
  2. Input      supplier entries (name, PDF path, submission date, experience rating)
  3. Batch      create supplier entries + one RFP_RUN_ID
  4. Evaluate   extract text -> build prompt -> call the LLM (per supplier)
  5. Validate   parse JSON, normalize missing/invalid criterion results
  6. Score      absolute weighted score per supplier
  7. Benchmark  best score per criterion; gaps; relative percentages
  8. Rank       PPI, tie-breaks, sequential ranks
  9. Persist    write complete results to SQLite under one RFP_RUN_ID
 10. Present    return the full result structure for the UI / export

The LLM judges proposal content only. All arithmetic, benchmarks, tie-breaks
and ranks are deterministic Python.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import db
from .llm import BaseLLMClient, LLMError
from .pdf_tools import PDFReadError, extract_text
from .ranking import rank_suppliers, tie_break_explanation
from .scoring import (
    absolute_weighted_score,
    compute_benchmarks,
    criterion_gap,
    peer_performance_index,
    relative_performance_pct,
)
from .validation import ValidationError, validate_llm_output

ProgressCallback = Callable[[str], None]


def _check_weights(criteria: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    total = sum(float(c["weight"]) for c in criteria)
    if abs(total - 100.0) > 0.01:
        warnings.append(
            f"Active criterion weights total {total:g}%, not 100%; "
            "scores are still computed proportionally."
        )
    return warnings


def run_evaluation(
    db_path: str | Path,
    suppliers: list[dict[str, Any]],
    llm_client: BaseLLMClient,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run a full evaluation batch. Returns the complete run result dict."""
    db_path = Path(db_path)
    criteria = db.get_active_criteria(db_path)
    if not criteria:
        raise ValueError("No active evaluation criteria found. Run scripts/init_db.py first.")
    if not suppliers:
        raise ValueError("No suppliers provided for evaluation.")

    warnings: list[str] = _check_weights(criteria)
    rfp_run_id = db.create_run(db_path)

    def note(msg: str) -> None:
        if progress:
            progress(msg)

    evaluated: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []

    for sup in suppliers:
        name = str(sup["name"]).strip()
        pdf_path = Path(sup["pdf_path"])
        submission_date = str(sup.get("submission_date") or "")
        experience_rating = float(sup.get("experience_rating") or 0)
        note(f"Evaluating {name} ...")
        try:
            text = extract_text(pdf_path)
            raw = llm_client.score_supplier(name, text, criteria)
            scorecard, sup_warnings = validate_llm_output(raw, criteria, name)
        except (PDFReadError, LLMError, ValidationError, ValueError) as exc:
            failed.append({"supplier_name": name, "error": str(exc)})
            warnings.append(f"Supplier '{name}' could not be evaluated and was skipped: {exc}")
            continue

        warnings.extend(sup_warnings)
        scores = {c["criterion_id"]: c["score"] for c in scorecard["criteria"]}
        absolute = absolute_weighted_score(scores, criteria)
        evaluated.append(
            {
                "supplier_name": name,
                "submission_date": submission_date,
                "experience_rating": experience_rating,
                "scorecard": scorecard,
                "scores": scores,
                "absolute_score": absolute,
                "warnings": sup_warnings,
            }
        )

    if not evaluated:
        raise RuntimeError(
            "No supplier could be evaluated successfully. "
            + (" ".join(f["error"] for f in failed) if failed else "")
        )

    # Benchmarks + peer metrics (deterministic).
    benchmarks = compute_benchmarks([e["scores"] for e in evaluated], criteria)
    weight_by_id = {int(c["criterion_id"]): float(c["weight"]) for c in criteria}
    name_by_id = {int(c["criterion_id"]): c["name"] for c in criteria}

    for e in evaluated:
        crit_details: list[dict[str, Any]] = []
        rel_pcts: dict[int, float] = {}
        for c in e["scorecard"]["criteria"]:
            cid = int(c["criterion_id"])
            bench = benchmarks[cid]
            rel = relative_performance_pct(float(c["score"]), bench)
            rel_pcts[cid] = rel
            crit_details.append(
                {
                    **c,
                    "weight": weight_by_id[cid],
                    "benchmark": bench,
                    "gap": criterion_gap(float(c["score"]), bench),
                    "relative_pct": rel,
                }
            )
        ppi = peer_performance_index(rel_pcts, criteria)
        e["ppi"] = ppi
        e["criterion_details"] = crit_details

    ranked = rank_suppliers(evaluated)

    # Persist everything under the single RFP_RUN_ID.
    for row in ranked:
        result_json = {
            "supplier_name": row["supplier_name"],
            "submission_date": row["submission_date"],
            "experience_rating": row["experience_rating"],
            "absolute_score": row["absolute_score"],
            "ppi": row["ppi"],
            "final_rank": row["final_rank"],
            "criteria": row["criterion_details"],
            "risks": row["scorecard"]["risks"],
            "overall_summary": row["scorecard"]["overall_summary"],
            "warnings": row["warnings"],
        }
        db.save_supplier_result(
            db_path,
            rfp_run_id,
            row["supplier_name"],
            row["submission_date"],
            row["experience_rating"],
            row["absolute_score"],
            row["ppi"],
            row["final_rank"],
            result_json,
        )

    note("Done.")
    return {
        "rfp_run_id": rfp_run_id,
        "criteria": criteria,
        "ranked": [
            {
                "final_rank": r["final_rank"],
                "supplier_name": r["supplier_name"],
                "submission_date": r["submission_date"],
                "experience_rating": r["experience_rating"],
                "absolute_score": r["absolute_score"],
                "ppi": r["ppi"],
            }
            for r in ranked
        ],
        "benchmarks": {name_by_id[cid]: b for cid, b in benchmarks.items()},
        "tie_break_order": tie_break_explanation(),
        "warnings": warnings,
        "failed_suppliers": failed,
    }
