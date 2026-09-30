"""Prompt builder for the Evaluation Agent.

The prompt is generated dynamically from the *active* criteria loaded from
SQLite, so changing criteria/weights in the database changes the prompt
without touching code.
"""

from __future__ import annotations

from typing import Any

# The exact JSON contract the model must return.
OUTPUT_SCHEMA_DOC = """{
  "supplier_name": "<supplier name>",
  "criteria": [
    {
      "criterion_id": <integer id from the criteria list>,
      "score": <number between 0 and max_score>,
      "max_score": <same max_score as listed>,
      "justification": "<1-3 sentences explaining the score>",
      "evidence": "<short verbatim quote(s) from the proposal supporting the score>"
    }
  ],
  "risks": ["<risk or gap spotted in the proposal>", "..."],
  "overall_summary": "<2-4 sentence overall assessment>"
}"""


def build_scoring_prompt(
    supplier_name: str,
    proposal_text: str,
    criteria: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return OpenAI-style chat messages asking for a criterion-wise scorecard."""
    criteria_block = "\n".join(
        f"- id {c['criterion_id']}: {c['name']} (max score {c['max_score']}, weight {c['weight']}%)\n"
        f"  What to inspect: {c['description']}"
        for c in criteria
    )
    n = len(criteria)
    system = (
        "You are a meticulous procurement analyst evaluating a supplier's RFP proposal. "
        "Score the proposal against EACH criterion below using ONLY evidence present in the "
        "proposal text. Do not invent capabilities, certifications, prices, or timelines that "
        "are not stated. If the proposal is weak or silent on a criterion, give a low score and "
        "say so plainly in the justification. Return JSON only - no markdown fences, no commentary."
    )
    user = f"""Evaluate the RFP proposal from supplier "{supplier_name}".

ACTIVE EVALUATION CRITERIA (return exactly one result for each of these {n}):
{criteria_block}

REQUIRED OUTPUT - valid JSON exactly matching this shape:
{OUTPUT_SCHEMA_DOC}

Rules:
1. "criteria" must contain exactly {n} entries, one per criterion id above, in order.
2. Each "score" must be a number within 0 and that criterion's max_score (decimals allowed).
3. "evidence" must be short verbatim quote(s) copied from the proposal. If no supporting
   text exists, write "No supporting evidence found in proposal." and score accordingly low.
4. "risks" lists concrete risks/gaps you spotted (empty list if none).
5. Output JSON ONLY.

PROPOSAL TEXT:
---
{proposal_text}
---"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
