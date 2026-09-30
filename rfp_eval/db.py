"""SQLite persistence layer.

Tables (per the project brief):
  evaluation_criteria  criterion_id, name, description, weight, max_score, is_active
  rfp_runs             rfp_run_id, created_at, status
  supplier_results     rfp_run_id, supplier_name, submission_date, experience_rating,
                       absolute_score, ppi, final_rank, result_json
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Weights of the seeded criteria (must total 100).
SEED_CRITERIA: list[dict[str, Any]] = [
    {
        "name": "Technical Capability",
        "description": "Architecture, integrations, scalability, technical fit",
        "weight": 30.0,
        "max_score": 10,
    },
    {
        "name": "Implementation Plan",
        "description": "Timeline, milestones, staffing, risk plan",
        "weight": 20.0,
        "max_score": 10,
    },
    {
        "name": "Commercial Value",
        "description": "Pricing clarity, total cost, assumptions",
        "weight": 20.0,
        "max_score": 10,
    },
    {
        "name": "Security & Compliance",
        "description": "Controls, certifications, privacy, auditability",
        "weight": 20.0,
        "max_score": 10,
    },
    {
        "name": "Support & Experience",
        "description": "Support model, similar projects, references",
        "weight": 10.0,
        "max_score": 10,
    },
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    weight REAL NOT NULL,
    max_score REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS rfp_runs (
    rfp_run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed'
);
CREATE TABLE IF NOT EXISTS supplier_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_run_id TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    submission_date TEXT NOT NULL,
    experience_rating REAL NOT NULL,
    absolute_score REAL NOT NULL,
    ppi REAL NOT NULL,
    final_rank INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    FOREIGN KEY (rfp_run_id) REFERENCES rfp_runs (rfp_run_id)
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    """Create all tables (idempotent)."""
    with connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def seed_criteria(db_path: str | Path, reset: bool = False) -> int:
    """Insert the sample criteria. Returns number of rows inserted."""
    with connect(db_path) as conn:
        if reset:
            conn.execute("DELETE FROM evaluation_criteria")
        existing = conn.execute("SELECT COUNT(*) AS n FROM evaluation_criteria").fetchone()["n"]
        if existing and not reset:
            return 0
        for c in SEED_CRITERIA:
            conn.execute(
                "INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active)"
                " VALUES (?, ?, ?, ?, 1)",
                (c["name"], c["description"], c["weight"], c["max_score"]),
            )
        return len(SEED_CRITERIA)


def get_active_criteria(db_path: str | Path) -> list[dict[str, Any]]:
    """Return active criteria ordered by criterion_id. Weights should total 100."""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT criterion_id, name, description, weight, max_score, is_active"
            " FROM evaluation_criteria WHERE is_active = 1 ORDER BY criterion_id"
        ).fetchall()
    return [dict(r) for r in rows]


def set_criterion_active(db_path: str | Path, criterion_id: int, is_active: bool) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE evaluation_criteria SET is_active = ? WHERE criterion_id = ?",
            (1 if is_active else 0, criterion_id),
        )


def update_criterion_weight(db_path: str | Path, criterion_id: int, weight: float) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE evaluation_criteria SET weight = ? WHERE criterion_id = ?",
            (weight, criterion_id),
        )


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"RFP-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def create_run(db_path: str | Path, rfp_run_id: str | None = None) -> str:
    rfp_run_id = rfp_run_id or new_run_id()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO rfp_runs (rfp_run_id, created_at, status) VALUES (?, ?, 'completed')",
            (rfp_run_id, created_at),
        )
    return rfp_run_id


def save_supplier_result(
    db_path: str | Path,
    rfp_run_id: str,
    supplier_name: str,
    submission_date: str,
    experience_rating: float,
    absolute_score: float,
    ppi: float,
    final_rank: int,
    result_json: dict[str, Any],
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO supplier_results (rfp_run_id, supplier_name, submission_date,"
            " experience_rating, absolute_score, ppi, final_rank, result_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rfp_run_id,
                supplier_name,
                submission_date,
                experience_rating,
                absolute_score,
                ppi,
                final_rank,
                json.dumps(result_json),
            ),
        )


def get_run_meta(db_path: str | Path, rfp_run_id: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT rfp_run_id, created_at, status FROM rfp_runs WHERE rfp_run_id = ?",
            (rfp_run_id,),
        ).fetchone()
    return dict(row) if row else None


def get_run_results(db_path: str | Path, rfp_run_id: str) -> list[dict[str, Any]]:
    """Supplier results for a run, ordered by final_rank."""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT supplier_name, submission_date, experience_rating, absolute_score,"
            " ppi, final_rank, result_json FROM supplier_results"
            " WHERE rfp_run_id = ? ORDER BY final_rank",
            (rfp_run_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["result_json"] = json.loads(d["result_json"])
        out.append(d)
    return out


def get_latest_run_id(db_path: str | Path) -> str | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT rfp_run_id FROM rfp_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    return row["rfp_run_id"] if row else None


def list_run_ids(db_path: str | Path) -> list[str]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT rfp_run_id FROM rfp_runs ORDER BY created_at DESC").fetchall()
    return [r["rfp_run_id"] for r in rows]
