"""Agentic RFP Evaluation and Supplier Ranking - Streamlit UI.

Screens (per the project brief):
  Criteria       active criteria, weights, maximum score
  Supplier input multiple PDF upload, supplier metadata, validation, Evaluate button
  Leaderboard    rank, supplier, absolute score, PPI, submission date, experience rating
  Scorecards     per-criterion score, benchmark, gap, relative %, weight, evidence, justification
  Run details    RFP_RUN_ID, warnings, tie-break explanation, JSON download
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rfp_eval import db
from rfp_eval.export import export_run_json
from rfp_eval.llm import get_client
from rfp_eval.pipeline import run_evaluation
from rfp_eval.ranking import TIE_BREAK_ORDER

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "rfp_eval.db"

st.set_page_config(page_title="Agentic RFP Evaluator", layout="wide")


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def ensure_db() -> None:
    db.init_db(DB_PATH)
    if not db.get_active_criteria(DB_PATH):
        db.seed_criteria(DB_PATH)


def _secret(name: str, default: str = "") -> str:
    """Read a key from Streamlit secrets or the environment (never hard-coded)."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # no secrets file locally
        pass
    return os.getenv(name, default)


OPENROUTER_URL = "https://openrouter.ai/api/v1"


def get_llm_client():
    provider = st.session_state.get("llm_provider", "Mock (no API key)")
    if provider.startswith("Mock"):
        return get_client("mock")
    if provider.startswith("OpenRouter"):
        return get_client(
            "openai",
            api_key=_secret("OPENROUTER_API_KEY"),
            model=_secret("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            base_url=OPENROUTER_URL,
        )
    return get_client(
        "openai",
        api_key=st.session_state.get("llm_api_key", ""),
        model=st.session_state.get("llm_model", "gpt-4o-mini"),
        base_url=st.session_state.get("llm_base_url") or None,
    )


# ---------------------------------------------------------------------------
# Sidebar - AI layer configuration
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("AI layer")
    st.selectbox(
        "Evaluation Agent",
        ["Mock (no API key)", "OpenRouter (key from secrets)", "OpenAI-compatible API"],
        key="llm_provider",
        help="The mock scorer is deterministic and needs no key. "
             "Choose OpenAI-compatible to use any JSON-capable chat model.",
    )
    if st.session_state.get("llm_provider", "").startswith("OpenRouter") and not _secret("OPENROUTER_API_KEY"):
        st.error("OPENROUTER_API_KEY is not set in Streamlit secrets or the environment.")
    if st.session_state.get("llm_provider", "").startswith("OpenAI"):
        st.text_input("Model", value="gpt-4o-mini", key="llm_model")
        st.text_input(
            "Base URL (optional)",
            value="",
            key="llm_base_url",
            placeholder="https://api.openai.com/v1",
            help="Leave empty for OpenAI; set for OpenRouter, Ollama, vLLM, ...",
        )
        st.text_input("API key", type="password", key="llm_api_key")
    st.divider()
    st.caption(f"Database: `{DB_PATH.name}`")
    if st.button("Reset demo database"):
        if DB_PATH.exists():
            DB_PATH.unlink()
        ensure_db()
        st.session_state.pop("run_id", None)
        st.success("Database reset and reseeded.")
        st.rerun()

ensure_db()

st.title("Agentic RFP Evaluation & Supplier Ranking")
st.caption(
    "An orchestrator agent reads supplier proposals, an LLM scores them against "
    "configurable criteria, and deterministic Python computes benchmarks, "
    "peer comparison, tie-breaks, and the final leaderboard."
)

tab_criteria, tab_input, tab_board, tab_cards, tab_run = st.tabs(
    ["Criteria", "Supplier input", "Leaderboard", "Scorecards", "Run details"]
)

# ---------------------------------------------------------------------------
# Tab: Criteria
# ---------------------------------------------------------------------------
with tab_criteria:
    st.subheader("Active evaluation criteria")
    criteria = db.get_active_criteria(DB_PATH)
    total_w = sum(c["weight"] for c in criteria)
    st.dataframe(
        [
            {
                "ID": c["criterion_id"],
                "Criterion": c["name"],
                "Weight %": c["weight"],
                "Max score": c["max_score"],
                "What the LLM inspects": c["description"],
            }
            for c in criteria
        ],
        use_container_width=True,
        hide_index=True,
    )
    if abs(total_w - 100.0) > 0.01:
        st.warning(f"Weights total {total_w:g}% - they should total 100%.")
    else:
        st.success(f"Weights total {total_w:g}%.")
    st.info(
        "Criteria live in SQLite (`evaluation_criteria`). Activate/deactivate them or "
        "change weights with `scripts/init_db.py`-style updates or any SQLite client - "
        "the evaluation prompt is generated from the database, no code changes needed."
    )

# ---------------------------------------------------------------------------
# Tab: Supplier input
# ---------------------------------------------------------------------------
with tab_input:
    st.subheader("Upload supplier RFPs")
    uploads = st.file_uploader(
        "Supplier proposal PDFs", type=["pdf"], accept_multiple_files=True,
        help="Upload one PDF per supplier.",
    )
    suppliers_meta: list[dict] = []
    if uploads:
        for i, uf in enumerate(uploads):
            default_name = Path(uf.name).stem.replace("_RFP_Response", "").replace("_", " ")
            with st.expander(f"Supplier {i + 1}: {uf.name}", expanded=(i == 0)):
                c1, c2, c3 = st.columns(3)
                name = c1.text_input("Supplier name", value=default_name, key=f"name_{i}")
                sub_date = c2.date_input("Submission date", value=date.today(), key=f"date_{i}")
                rating = c3.slider("Experience rating (1-5)", 1.0, 5.0, 3.0, 0.5, key=f"rating_{i}")
                suppliers_meta.append(
                    {"name": name.strip(), "submission_date": sub_date.isoformat(),
                     "experience_rating": rating, "file": uf}
                )

    can_run = True
    if uploads:
        names = [s["name"] for s in suppliers_meta]
        if any(not n for n in names):
            st.error("Every supplier needs a name.")
            can_run = False
        if len(set(names)) != len(names):
            st.error("Supplier names must be unique.")
            can_run = False

    if st.button("Evaluate suppliers", type="primary", disabled=not uploads or not can_run):
        provider_now = st.session_state.get("llm_provider", "")
        if provider_now.startswith("OpenAI") and not st.session_state.get("llm_api_key"):
            st.error("Enter an API key in the sidebar (or switch to the Mock agent).")
        elif provider_now.startswith("OpenRouter") and not _secret("OPENROUTER_API_KEY"):
            st.error("OPENROUTER_API_KEY is missing from Streamlit secrets (or switch to the Mock agent).")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                batch = []
                for s in suppliers_meta:
                    pdf_path = Path(tmp) / f"{s['name']}.pdf"
                    pdf_path.write_bytes(s["file"].getbuffer())
                    batch.append(
                        {"name": s["name"], "pdf_path": pdf_path,
                         "submission_date": s["submission_date"],
                         "experience_rating": s["experience_rating"]}
                    )
                progress = st.empty()
                try:
                    result = run_evaluation(
                        DB_PATH, batch, get_llm_client(),
                        progress=lambda m: progress.info(m),
                    )
                except Exception as exc:  # noqa: BLE001 - show any pipeline failure
                    st.error(f"Evaluation failed: {exc}")
                else:
                    progress.empty()
                    st.session_state["run_id"] = result["rfp_run_id"]
                    st.success(f"Evaluation complete. RFP_RUN_ID = `{result['rfp_run_id']}`")
                    if result["warnings"]:
                        with st.expander(f"Warnings ({len(result['warnings'])})"):
                            for w in result["warnings"]:
                                st.write(f"- {w}")
                    if result["failed_suppliers"]:
                        st.warning(
                            "Skipped: " + ", ".join(
                                f"{f['supplier_name']} ({f['error']})"
                                for f in result["failed_suppliers"]
                            )
                        )
                    st.info("See the Leaderboard and Scorecards tabs for the results.")

# ---------------------------------------------------------------------------
# Shared: run selection
# ---------------------------------------------------------------------------
def current_run_id() -> str | None:
    run_ids = db.list_run_ids(DB_PATH)
    if not run_ids:
        return None
    selected = st.session_state.get("run_id")
    return selected if selected in run_ids else run_ids[0]

# ---------------------------------------------------------------------------
# Tab: Leaderboard
# ---------------------------------------------------------------------------
with tab_board:
    st.subheader("Leaderboard")
    run_id = current_run_id()
    if not run_id:
        st.info("No evaluation runs yet. Upload supplier PDFs in the Supplier input tab.")
    else:
        results = db.get_run_results(DB_PATH, run_id)
        st.caption(f"Showing run `{run_id}` (change runs in the Run details tab).")
        st.dataframe(
            [
                {
                    "Rank": r["final_rank"],
                    "Supplier": r["supplier_name"],
                    "Absolute score (/100)": r["absolute_score"],
                    "PPI": r["ppi"],
                    "Submission date": r["submission_date"],
                    "Experience rating": r["experience_rating"],
                }
                for r in results
            ],
            use_container_width=True,
            hide_index=True,
        )
        if results:
            winner = results[0]
            st.success(
                f"Winner: **{winner['supplier_name']}** - absolute score "
                f"{winner['absolute_score']}, PPI {winner['ppi']}."
            )

# ---------------------------------------------------------------------------
# Tab: Scorecards
# ---------------------------------------------------------------------------
with tab_cards:
    st.subheader("Detailed scorecards")
    run_id = current_run_id()
    if not run_id:
        st.info("No evaluation runs yet.")
    else:
        results = db.get_run_results(DB_PATH, run_id)
        names = [r["supplier_name"] for r in results]
        chosen = st.selectbox("Supplier", names)
        row = next(r for r in results if r["supplier_name"] == chosen)
        detail = row["result_json"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rank", detail["final_rank"])
        m2.metric("Absolute score", detail["absolute_score"])
        m3.metric("PPI", detail["ppi"])
        m4.metric("Experience", detail["experience_rating"])
        st.write(f"**Overall:** {detail['overall_summary']}")
        if detail["risks"]:
            with st.expander(f"Risks / gaps ({len(detail['risks'])})"):
                for risk in detail["risks"]:
                    st.write(f"- {risk}")
        st.divider()
        for c in detail["criteria"]:
            flags = []
            if c.get("imputed"):
                flags.append("imputed")
            if c.get("clipped"):
                flags.append("clipped")
            flag_txt = f" ({', '.join(flags)})" if flags else ""
            with st.expander(
                f"{c['name']} - {c['score']}/{c['max_score']:g}{flag_txt} "
                f"(benchmark {c['benchmark']}, gap {c['gap']:+g}, rel. {c['relative_pct']}%)"
            ):
                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric("Score", f"{c['score']}/{c['max_score']:g}")
                cc2.metric("Benchmark", c["benchmark"])
                cc3.metric("Gap", f"{c['gap']:+g}")
                cc4.metric("Relative %", f"{c['relative_pct']}%")
                st.write(f"**Weight:** {c['weight']}%")
                st.write(f"**Justification:** {c['justification']}")
                st.write(f"**Evidence:** {c['evidence'] or '—'}")
        if detail["warnings"]:
            with st.expander(f"Validation warnings ({len(detail['warnings'])})"):
                for w in detail["warnings"]:
                    st.write(f"- {w}")

# ---------------------------------------------------------------------------
# Tab: Run details
# ---------------------------------------------------------------------------
with tab_run:
    st.subheader("Run details")
    run_ids = db.list_run_ids(DB_PATH)
    if not run_ids:
        st.info("No evaluation runs yet.")
    else:
        chosen_run = st.selectbox("RFP run", run_ids,
                                  index=run_ids.index(current_run_id()))
        st.session_state["run_id"] = chosen_run
        meta = db.get_run_meta(DB_PATH, chosen_run)
        st.write(f"**RFP_RUN_ID:** `{chosen_run}`")
        st.write(f"**Created:** {meta['created_at']} (UTC)")
        st.write(f"**Status:** {meta['status']}")
        st.write("**Tie-break order:**")
        for i, step in enumerate(TIE_BREAK_ORDER, start=1):
            st.write(f"{i}. {step}")
        st.write(
            "Ranks 1, 2, 3, ... are assigned sequentially only after this stable sort, "
            "so identical validated scorecards always produce identical rankings."
        )
        payload = export_run_json(DB_PATH, chosen_run)
        st.download_button(
            "Download complete run as JSON",
            data=json.dumps(payload, indent=2),
            file_name=f"{chosen_run}.json",
            mime="application/json",
        )
