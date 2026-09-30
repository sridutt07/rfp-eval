"""Create the SQLite database and seed the sample evaluation criteria.

Usage:
    python scripts/init_db.py [--db data/rfp_eval.db] [--reset]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rfp_eval import db

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "rfp_eval.db"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and seed the RFP evaluation database.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    parser.add_argument("--reset", action="store_true", help="Drop and reseed criteria")
    args = parser.parse_args()

    db.init_db(args.db)
    inserted = db.seed_criteria(args.db, reset=args.reset)
    criteria = db.get_active_criteria(args.db)
    total_weight = sum(c["weight"] for c in criteria)

    print(f"Database ready: {args.db}")
    print(f"Seeded {inserted} criteria ({len(criteria)} active, weights total {total_weight:g}%)")
    for c in criteria:
        print(f"  [{c['criterion_id']}] {c['name']:<22} weight={c['weight']:g}%  max={c['max_score']:g}")


if __name__ == "__main__":
    main()
