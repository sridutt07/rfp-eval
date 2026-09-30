"""JSON export of a completed RFP run (for download / submission)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import db
from .ranking import tie_break_explanation


def export_run_json(db_path: str | Path, rfp_run_id: str) -> dict[str, Any]:
    """Build the complete, self-contained JSON document for a run."""
    meta = db.get_run_meta(db_path, rfp_run_id)
    if meta is None:
        raise ValueError(f"Unknown RFP run id: {rfp_run_id}")
    results = db.get_run_results(db_path, rfp_run_id)

    criteria_snapshot: list[dict[str, Any]] = []
    if results:
        for c in results[0]["result_json"]["criteria"]:
            criteria_snapshot.append(
                {
                    "criterion_id": c["criterion_id"],
                    "name": c["name"],
                    "weight": c["weight"],
                    "max_score": c["max_score"],
                }
            )

    warnings: list[str] = []
    suppliers: list[dict[str, Any]] = []
    for r in results:
        detail = r["result_json"]
        warnings.extend(detail.get("warnings", []))
        suppliers.append(
            {
                "final_rank": r["final_rank"],
                "supplier_name": r["supplier_name"],
                "submission_date": r["submission_date"],
                "experience_rating": r["experience_rating"],
                "absolute_score": r["absolute_score"],
                "ppi": r["ppi"],
                "criteria": detail["criteria"],
                "risks": detail.get("risks", []),
                "overall_summary": detail.get("overall_summary", ""),
            }
        )

    return {
        "rfp_run_id": rfp_run_id,
        "created_at": meta["created_at"],
        "status": meta["status"],
        "criteria": criteria_snapshot,
        "tie_break_order": tie_break_explanation(),
        "warnings": warnings,
        "suppliers": suppliers,
    }


def write_run_json(db_path: str | Path, rfp_run_id: str, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = export_run_json(db_path, rfp_run_id)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
