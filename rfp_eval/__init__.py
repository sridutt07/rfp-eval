"""Agentic RFP Evaluation and Supplier Ranking.

Package layout (mirrors the agentic design in the project brief):

- db.py          SQLite persistence (criteria, runs, supplier results)
- pdf_tools.py   Document Tool: PDF text extraction
- prompts.py     Prompt builder used by the Evaluation Agent
- llm.py         AI layer: Evaluation Agent (real LLM or deterministic mock)
- validation.py  Validation Tool: schema checks + normalization
- scoring.py     Deterministic scoring math (weighted scores, benchmarks, PPI)
- ranking.py     Ranking Tool: peer comparison, tie-breaks, final ranks
- pipeline.py    Orchestrator Agent: runs the whole workflow end to end
- export.py      JSON export of a completed run
"""

__version__ = "1.0.0"
