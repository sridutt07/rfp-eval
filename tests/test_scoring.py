"""Tests for the deterministic parts of the workflow.

The brief's success condition: the same inputs must always produce the same
formulas and ordering once the LLM scorecards have been validated. The LLM
itself is covered by the deterministic mock, not by these tests.
"""

from __future__ import annotations

import pytest

from rfp_eval import db
from rfp_eval.llm import get_client
from rfp_eval.pipeline import run_evaluation
from rfp_eval.ranking import rank_suppliers
from rfp_eval.scoring import (
    absolute_weighted_score,
    compute_benchmarks,
    criterion_gap,
    peer_performance_index,
    relative_performance_pct,
)
from rfp_eval.validation import ValidationError, validate_llm_output

CRITERIA = [
    {"criterion_id": 1, "name": "Technical Capability", "description": "t",
     "weight": 30.0, "max_score": 10, "is_active": 1},
    {"criterion_id": 2, "name": "Implementation Plan", "description": "t",
     "weight": 20.0, "max_score": 10, "is_active": 1},
    {"criterion_id": 3, "name": "Commercial Value", "description": "t",
     "weight": 20.0, "max_score": 10, "is_active": 1},
    {"criterion_id": 4, "name": "Security & Compliance", "description": "t",
     "weight": 20.0, "max_score": 10, "is_active": 1},
    {"criterion_id": 5, "name": "Support & Experience", "description": "t",
     "weight": 10.0, "max_score": 10, "is_active": 1},
]


# --- scoring ---------------------------------------------------------------

def test_absolute_weighted_score():
    scores = {1: 8.0, 2: 6.0, 3: 10.0, 4: 5.0, 5: 9.0}
    # 0.8*30 + 0.6*20 + 1.0*20 + 0.5*20 + 0.9*10 = 24+12+20+10+9 = 75
    assert absolute_weighted_score(scores, CRITERIA) == 75.0


def test_benchmarks_gaps_relative():
    all_scores = [{1: 8.0, 2: 6.0}, {1: 5.0, 2: 9.0}]
    bench = compute_benchmarks(all_scores, CRITERIA[:2])
    assert bench == {1: 8.0, 2: 9.0}
    assert criterion_gap(5.0, 8.0) == -3.0
    assert criterion_gap(8.0, 8.0) == 0.0
    assert relative_performance_pct(4.0, 8.0) == 50.0
    assert relative_performance_pct(0.0, 0.0) == 100.0  # safe zero-benchmark handling


def test_ppi_is_weighted_average_of_relative_pcts():
    rel = {1: 100.0, 2: 50.0, 3: 50.0, 4: 0.0, 5: 100.0}
    # (100*30 + 50*20 + 50*20 + 0*20 + 100*10) / 100 = 60
    assert peer_performance_index(rel, CRITERIA) == 60.0


# --- ranking / tie-breaks ---------------------------------------------------

def _row(name, ppi, date, rating):
    return {"supplier_name": name, "ppi": ppi, "submission_date": date,
            "experience_rating": rating}


def test_tiebreak_ppi_then_date_then_rating_then_name():
    rows = [
        _row("Beta", 80.0, "2026-09-10", 5),   # later date loses to Alpha
        _row("Alpha", 80.0, "2026-09-09", 3),  # wins on earlier date
        _row("Gamma", 90.0, "2026-09-12", 1),  # wins on PPI outright
        _row("delta", 80.0, "2026-09-09", 3),  # same as Alpha -> name order: Alpha < delta
    ]
    ranked = rank_suppliers(rows)
    assert [r["supplier_name"] for r in ranked] == ["Gamma", "Alpha", "delta", "Beta"]
    assert [r["final_rank"] for r in ranked] == [1, 2, 3, 4]


def test_tiebreak_rating_before_name():
    rows = [
        _row("Zeta", 70.0, "2026-09-09", 2),
        _row("Aaron", 70.0, "2026-09-09", 4),  # higher rating wins despite later name
    ]
    ranked = rank_suppliers(rows)
    assert [r["supplier_name"] for r in ranked] == ["Aaron", "Zeta"]


# --- validation ------------------------------------------------------------

def test_validation_clips_imputes_and_warns():
    raw = {
        "supplier_name": "X",
        "criteria": [
            {"criterion_id": 1, "score": 99, "max_score": 10,
             "justification": "j", "evidence": "e"},          # clipped to 10
            {"criterion_id": 2, "score": "abc", "max_score": 10,
             "justification": "j", "evidence": "e"},          # unparseable -> 0
            # criterion 3 missing -> imputed 0
            {"criterion_id": 4, "score": 7, "max_score": 10,
             "justification": "", "evidence": ""},            # missing texts -> warnings
            {"criterion_id": 5, "score": 6, "max_score": 10,
             "justification": "j", "evidence": "e"},
            {"criterion_id": 42, "score": 10, "max_score": 10,
             "justification": "j", "evidence": "e"},          # unknown id ignored
        ],
        "risks": [],
        "overall_summary": "ok",
    }
    norm, warnings = validate_llm_output(raw, CRITERIA, "X")
    by_id = {c["criterion_id"]: c for c in norm["criteria"]}
    assert by_id[1]["score"] == 10.0 and by_id[1]["clipped"] is True
    assert by_id[2]["score"] == 0.0
    assert by_id[3]["score"] == 0.0 and by_id[3]["imputed"] is True
    assert 42 not in by_id
    assert any("clipped" in w for w in warnings)
    assert any("imputed" in w for w in warnings)
    assert any("unknown criterion_id 42" in w for w in warnings)


def test_validation_rejects_broken_structure():
    with pytest.raises(ValidationError):
        validate_llm_output({"nope": 1}, CRITERIA, "X")
    with pytest.raises(ValidationError):
        validate_llm_output("not a dict", CRITERIA, "X")


# --- database ---------------------------------------------------------------

def test_db_roundtrip(tmp_path):
    db_path = tmp_path / "t.db"
    db.init_db(db_path)
    assert db.seed_criteria(db_path) == 5
    assert len(db.get_active_criteria(db_path)) == 5
    run_id = db.create_run(db_path)
    db.save_supplier_result(db_path, run_id, "Acme", "2026-09-01", 4.0,
                            80.0, 95.0, 1, {"hello": "world"})
    results = db.get_run_results(db_path, run_id)
    assert len(results) == 1
    assert results[0]["supplier_name"] == "Acme"
    assert results[0]["result_json"] == {"hello": "world"}
    assert db.get_latest_run_id(db_path) == run_id


# --- end-to-end determinism ---------------------------------------------------

def test_pipeline_is_deterministic(tmp_path):
    from pathlib import Path

    pdf_dir = Path(__file__).resolve().parent.parent / "data" / "sample_pdfs"
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    assert len(pdfs) >= 4, "run scripts/make_sample_pdfs.py first"

    def run_once(db_file):
        db.init_db(db_file)
        db.seed_criteria(db_file)
        suppliers = [
            {"name": p.stem.replace("_RFP_Response", "").replace("_", " "),
             "pdf_path": p, "submission_date": "2026-09-10", "experience_rating": 3}
            for p in pdfs
        ]
        return run_evaluation(db_file, suppliers, get_client("mock"))

    r1 = run_once(tmp_path / "a.db")
    r2 = run_once(tmp_path / "b.db")
    assert r1["ranked"] == r2["ranked"]
    # Leaderboard is complete and sequential
    assert [r["final_rank"] for r in r1["ranked"]] == [1, 2, 3, 4]
