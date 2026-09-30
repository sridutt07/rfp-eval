# Agentic RFP Evaluation & Supplier Ranking

Upload supplier RFP PDFs. An LLM scores each proposal against configurable criteria; plain Python then validates the scores, benchmarks suppliers against each other, and produces a ranked, explainable leaderboard stored in SQLite.

**Live app:** https://rfp-eval-qsspy7fqn479mpep8cqsau.streamlit.app
**Source:** https://github.com/sridutt07/rfp-eval

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py          # create + seed the database
python scripts/make_sample_pdfs.py # (optional) regenerate the 4 fictional PDFs
python scripts/demo.py             # success run + validation cases
pytest                             # unit tests
streamlit run app.py               # web UI
```

No API key is needed: a built-in mock agent works out of the box. For a real model, pick **OpenRouter (key from secrets)** in the sidebar after setting `OPENROUTER_API_KEY` (optional `OPENROUTER_MODEL`, default `openai/gpt-4o-mini`) in `.streamlit/secrets.toml` or the environment. **OpenAI-compatible API** lets you type in a key, model and base URL instead.

## Architecture

```
PDFs → extract text → LLM scores each criterion → validate → calculate → rank → SQLite → UI + JSON
       (PyMuPDF)      (OpenRouter, gpt-4o-mini)   (Python)    (Python)     (Python)
```

| Step | Module | Uses LLM? |
|---|---|---|
| Orchestrate the run | `pipeline.py` | No |
| Extract PDF text | `pdf_tools.py` | No |
| Score each criterion, with justification and evidence | `llm.py`, `prompts.py` | **Yes** (only step) |
| Fix missing / invalid / out-of-range scores | `validation.py` | No |
| Weighted score, benchmark, gap, relative %, PPI | `scoring.py` | No |
| Tie-breaks and ranks | `ranking.py` | No |
| Store results, export JSON | `db.py`, `export.py` | No |

Criteria, weights and max scores come from SQLite, so they can change without touching code. The LLM never does arithmetic or ranking. Its scores are the only non-deterministic input, so the same *validated* scorecards always give the same ranking.

## Database (SQLite)

- `evaluation_criteria`: `criterion_id, name, description, weight, max_score, is_active`
- `rfp_runs`: `rfp_run_id, created_at, status`
- `supplier_results`: `rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json`

Seeded criteria: Technical Capability 30%, Implementation Plan 20%, Commercial Value 20%, Security & Compliance 20%, Support & Experience 10% (max score 10 each).

## Formulas

- **Absolute score** = Σ (score / max score × weight), on a 0–100 scale
- **Benchmark** = best score for that criterion across all suppliers
- **Gap** = score − benchmark (0 for the leader, otherwise negative)
- **Relative %** = score / benchmark × 100 (100 if the benchmark is 0)
- **PPI** = weighted average of the relative %
- **Ranking** = sort by higher PPI, then earlier submission date, then higher experience rating, then supplier name A–Z. Ranks 1, 2, 3… are assigned after the sort.

## Validation

| Problem in LLM output | Handling |
|---|---|
| Missing criterion | Score 0, warning |
| Non-numeric score | Converted if possible, else 0 |
| Score outside 0 to max | Clipped, warning |
| Wrong `max_score` | Database value used |
| Duplicate or unknown criterion id | First kept / ignored, warning |
| Missing justification, evidence or summary | Default text, warning |
| No criteria list at all | Supplier skipped with an error |

## Demo

**Videos** (deployed app, live LLM via OpenRouter):

- [`Success_verification.webm`](OUTPUT_INFO/Videos/Success_verification.webm): successful run
- [`Diffrent_dates_ratings.webm`](OUTPUT_INFO/Videos/Diffrent_dates_ratings.webm): successful run with different dates and ratings (run `RFP-20260930-C5F34D`)
- [`Dublicate_File_validation_error.webm`](OUTPUT_INFO/Videos/Dublicate_File_validation_error.webm): duplicate supplier name blocks evaluation

**Exported JSON** (full result of a run):

- [`OUTPUT_INFO/Diffrent_Dates_ranking.json`](OUTPUT_INFO/Diffrent_Dates_ranking.json): live run `RFP-20260930-C5F34D` (matches the screenshots)
- [`OUTPUT_INFO/Inital_run.json`](OUTPUT_INFO/Inital_run.json): first live run
- [`sample_output/sample_run.json`](sample_output/sample_run.json): mock-agent run from `scripts/demo.py`

In the different-dates run every supplier has a distinct PPI, so PPI alone decides the order. The date, rating and name tie-breaks are covered by `tests/test_scoring.py`. Live LLM scores can vary slightly between runs.

## Screenshots

**Leaderboard**
![Leaderboard](docs/leaderboard.png)

**Detailed scorecard**
![Detailed scorecard](docs/scorecard.png)

**Run details**
![Run details](docs/run-details.png)

**Validation error: duplicate supplier name**
![Duplicate name validation error](docs/validation-error-duplicate-name.png)

## Deploy on Streamlit Community Cloud

1. Push the repo to GitHub (`.venv`, `.env` and `secrets.toml` are git-ignored).
2. At share.streamlit.io, create a new app: branch `main`, main file `app.py`, Python 3.11.
3. For a real model, add to the app's *Secrets*: `OPENROUTER_API_KEY = "your-key"`, then choose **OpenRouter (key from secrets)** in the sidebar. The URL is public, so set a spend limit on the key.

## Assumptions

- Scores run from 0 to each criterion's max score; active weights should total 100%.
- Submission dates are `YYYY-MM-DD`; experience rating is 1–5, higher is better.
- All supplier PDFs are fictional (`data/sample_pdfs/`, generated by `scripts/make_sample_pdfs.py`).

## Project layout

```
app.py          Streamlit UI
rfp_eval/       pipeline, pdf_tools, llm, prompts, validation, scoring, ranking, db, export
scripts/        init_db.py, make_sample_pdfs.py, demo.py
tests/          unit tests
data/           sample PDFs, SQLite database (generated)
OUTPUT_INFO/    demo videos and exported JSON
docs/           README screenshots
sample_output/  mock-agent run JSON
```