"""Headless demonstration of the agentic RFP evaluation workflow.

Part 1 (success case): runs the full pipeline on the four synthetic supplier
PDFs with the deterministic mock LLM, prints the leaderboard, and writes
sample_output/sample_run.json.

Part 2 (validation case): feeds deliberately malformed LLM outputs through
the Validation Tool to show schema checks, clipping, imputation, and warnings.

Usage:
    python scripts/demo.py [--db data/rfp_eval.db] [--provider mock]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rfp_eval import db
from rfp_eval.export import write_run_json
from rfp_eval.llm import get_client
from rfp_eval.pipeline import run_evaluation
from rfp_eval.validation import ValidationError, validate_llm_output

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "rfp_eval.db"
PDF_DIR = ROOT / "data" / "sample_pdfs"

# Supplier metadata for the demo batch (dates/ratings chosen to exercise tie-breaks).
DEMO_SUPPLIERS = [
    {"file": "Apex_Systems_RFP_Response.pdf", "name": "Apex Systems",
     "submission_date": "2026-09-10", "experience_rating": 4},
    {"file": "BrightPath_Tech_RFP_Response.pdf", "name": "BrightPath Tech",
     "submission_date": "2026-09-11", "experience_rating": 2},
    {"file": "NexaWorks_RFP_Response.pdf", "name": "NexaWorks",
     "submission_date": "2026-09-12", "experience_rating": 4},
    {"file": "Orbit_Digital_RFP_Response.pdf", "name": "Orbit Digital",
     "submission_date": "2026-09-09", "experience_rating": 5},
]


def part1_success(db_path: Path, provider: str, llm_kwargs: dict) -> str:
    print("=" * 72)
    print("PART 1 - Successful end-to-end run (Orchestrator -> Document Tool ->")
    print("        Evaluation Agent -> Validation Tool -> Ranking Tool -> SQLite)")
    print("=" * 72)
    db.init_db(db_path)
    db.seed_criteria(db_path)

    suppliers = [
        {
            "name": s["name"],
            "pdf_path": PDF_DIR / s["file"],
            "submission_date": s["submission_date"],
            "experience_rating": s["experience_rating"],
        }
        for s in DEMO_SUPPLIERS
    ]
    missing = [s["pdf_path"].name for s in suppliers if not Path(s["pdf_path"]).exists()]
    if missing:
        raise SystemExit(
            f"Sample PDFs missing: {missing}. Run: python scripts/make_sample_pdfs.py"
        )

    client = get_client(provider, **llm_kwargs)
    result = run_evaluation(db_path, suppliers, client, progress=print)

    print(f"\nRFP_RUN_ID: {result['rfp_run_id']}")
    print(f"{'Rank':<6}{'Supplier':<18}{'Abs score':<11}{'PPI':<8}{'Submitted':<12}{'Exp'}")
    for r in result["ranked"]:
        print(f"{r['final_rank']:<6}{r['supplier_name']:<18}{r['absolute_score']:<11}"
              f"{r['ppi']:<8}{r['submission_date']:<12}{r['experience_rating']}")
    print(f"\nTie-break order: {result['tie_break_order']}")
    if result["warnings"]:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for w in result["warnings"][:8]:
            print(f"  - {w}")
    if result["failed_suppliers"]:
        print(f"\nFailed suppliers: {result['failed_suppliers']}")

    out = write_run_json(db_path, result["rfp_run_id"], ROOT / "sample_output" / "sample_run.json")
    print(f"\nSample JSON exported to: {out}")
    return result["rfp_run_id"]


def part2_validation(db_path: Path) -> None:
    print("\n" + "=" * 72)
    print("PART 2 - Validation / error cases (Validation Tool)")
    print("=" * 72)
    criteria = db.get_active_criteria(db_path)

    cases = {
        "out-of-range + string scores + unknown id": {
            "supplier_name": "Bogus Corp",
            "criteria": [
                {"criterion_id": 1, "score": 14, "max_score": 10,  # clipped to 10
                 "justification": "Amazing.", "evidence": "We are amazing."},
                {"criterion_id": 2, "score": "7.5", "max_score": 10,  # coerced
                 "justification": "Fine.", "evidence": "We are fine."},
                {"criterion_id": 99, "score": 9, "max_score": 10,  # unknown id
                 "justification": "?", "evidence": "?"},
                # criterion 3 missing -> imputed 0; 4 has junk score; 5 empty strings
                {"criterion_id": 4, "score": "excellent", "max_score": 10,
                 "justification": "Trust us.", "evidence": ""},
                {"criterion_id": 5, "score": 6, "max_score": 5,  # max mismatch -> db wins
                 "justification": "", "evidence": ""},
            ],
            "risks": "not a list",  # reset to []
            "overall_summary": "",
        },
        "duplicate criterion ids": {
            "supplier_name": "Dup Corp",
            "criteria": [
                {"criterion_id": 1, "score": 9, "max_score": 10,
                 "justification": "First.", "evidence": "E1."},
                {"criterion_id": 1, "score": 2, "max_score": 10,
                 "justification": "Second.", "evidence": "E2."},
            ],
            "risks": [],
            "overall_summary": "Dup.",
        },
    }

    for title, raw in cases.items():
        print(f"\n--- Case: {title} ---")
        normalized, warnings = validate_llm_output(raw, criteria, "Test Supplier")
        scores = {c["name"]: c["score"] for c in normalized["criteria"]}
        print("Normalized scores:", json.dumps(scores))
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    print("\n--- Case: structurally broken output ---")
    try:
        validate_llm_output({"nope": True}, criteria, "Broken Corp")
    except ValidationError as exc:
        print(f"ValidationError (expected): {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo the RFP evaluation workflow.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--provider", default="mock",
                        help="'mock' (default, no key) or 'openai' (OpenAI-compatible)")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    import os
    llm_kwargs = {"model": args.model, "base_url": args.base_url,
                  "api_key": args.api_key or os.environ.get("OPENAI_API_KEY", "")}
    part1_success(Path(args.db), args.provider, llm_kwargs)
    part2_validation(Path(args.db))
    print("\nDemo complete.")


if __name__ == "__main__":
    main()
