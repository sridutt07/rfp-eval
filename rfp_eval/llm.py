"""AI layer: the Evaluation Agent.

Two implementations behind one interface:

- OpenAICompatibleClient: calls any JSON-capable chat model through an
  OpenAI-compatible API (OpenAI, OpenRouter, Ollama, vLLM, ...).
- MockLLMClient: a fully deterministic, keyword-evidence scorer that needs no
  API key. Used for demos, tests, and the sample run so the project works
  out of the box.

The orchestrator only depends on the ``score_supplier`` interface, so the
model can be swapped without touching the workflow.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .prompts import build_scoring_prompt


class LLMError(Exception):
    """Raised when the model call fails or returns unusable output."""


class BaseLLMClient:
    def score_supplier(
        self,
        supplier_name: str,
        proposal_text: str,
        criteria: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raise NotImplementedError


class OpenAICompatibleClient(BaseLLMClient):
    """Chat-completions client for any OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is required for real-model scoring. "
                "Install it with: pip install openai"
            ) from exc
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def score_supplier(self, supplier_name, proposal_text, criteria) -> dict[str, Any]:
        messages = build_scoring_prompt(supplier_name, proposal_text, criteria)
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Some providers reject response_format; retry without it (prompt says JSON only).
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=0,
                )
            except Exception as exc:
                raise LLMError(f"Model call failed: {exc}") from exc
        content = (response.choices[0].message.content or "").strip()
        # Tolerate markdown fences in case the model adds them anyway.
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model did not return valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise LLMError("Model returned a JSON value that is not an object.")
        return data


# ---------------------------------------------------------------------------
# Deterministic mock scorer
# ---------------------------------------------------------------------------

# Keyword signals per criterion (matched against normalized criterion names).
# The synthetic proposals in data/sample_pdfs were written against these signals,
# which is what makes the mock's scorecards sensible and reproducible.
_CRITERION_SIGNALS: dict[str, dict[str, list[str]]] = {
    "technical capability": {
        "positive": [
            "architecture", "scalable", "scalability", "integration", "api",
            "microservices", "cloud-native", "real-time", "platform",
            "redundant", "kubernetes", "event-driven", "open standards",
        ],
        "negative": ["vague", "unclear", "limited detail", "not specified", "missing detail"],
    },
    "implementation plan": {
        "positive": [
            "milestone", "timeline", "phase", "staffing", "go-live", "deliverable",
            "project plan", "workshop", "cutover", "pilot",
        ],
        "negative": ["vague", "unclear", "no timeline", "not specified", "missing detail"],
    },
    "commercial value": {
        "positive": [
            "fixed price", "transparent pricing", "assumptions", "payment terms",
            "cost breakdown", "total cost", "not-to-exceed",
        ],
        "negative": ["premium pricing", "higher price", "expensive", "cost overrun", "unclear pricing"],
    },
    "security & compliance": {
        "positive": [
            "iso 27001", "soc 2", "encryption", "gdpr", "audit", "certification",
            "penetration test", "access control", "data privacy", "compliance",
        ],
        "negative": ["weak", "limited detail", "not specified", "missing", "unclear"],
    },
    "support & experience": {
        "positive": [
            "24/7", "sla", "support", "reference", "experience", "track record",
            "helpdesk", "account manager", "similar project",
        ],
        "negative": ["limited experience", "few references", "not specified", "missing"],
    },
}

_GENERIC_SIGNALS = {
    "positive": ["strong", "proven", "detailed", "comprehensive", "robust"],
    "negative": ["weak", "vague", "unclear", "limited", "missing"],
}


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    # Collapse all whitespace (including newlines from PDF extraction) so that
    # multi-word keywords like "account manager" match across line breaks.
    return [
        cleaned
        for p in parts
        if len(cleaned := re.sub(r"\s+", " ", p).strip()) > 25
    ]


def _find_hits(sentences: list[str], keywords: list[str]) -> list[tuple[str, list[str]]]:
    """Return [(sentence, matched_keywords)] for sentences containing any keyword."""
    hits = []
    for s in sentences:
        low = s.lower()
        matched = [k for k in keywords if k in low]
        if matched:
            hits.append((s, matched))
    return hits


class MockLLMClient(BaseLLMClient):
    """Deterministic evidence-grounded scorer. No network, no API key.

    For each criterion it finds proposal sentences mentioning that criterion's
    keyword signals, measures distinct keyword coverage versus negative cues,
    and maps them onto the 0..max_score scale. Matching is negation-aware:
    a sentence containing a negative cue (e.g. "certifications are not
    specified") never counts as positive evidence. The same inputs always
    produce the same scorecard.
    """

    def score_supplier(self, supplier_name, proposal_text, criteria) -> dict[str, Any]:
        sentences = _split_sentences(proposal_text)
        out_criteria: list[dict[str, Any]] = []
        risks: list[str] = []

        for c in criteria:
            key = str(c["name"]).strip().lower()
            signals = _CRITERION_SIGNALS.get(key, _GENERIC_SIGNALS)
            max_score = float(c["max_score"])

            pos_hits = _find_hits(sentences, signals["positive"])
            neg_hits = _find_hits(sentences, signals["negative"])
            # Negation-aware: a sentence that itself contains a negative cue
            # (e.g. "certifications are not specified") must not count as
            # positive evidence for that criterion.
            negated = {s for s, _ in neg_hits}
            distinct_pos = {k for s, m in pos_hits if s not in negated for k in m}
            neg_count = sum(len(m) for _, m in neg_hits)

            raw = 4.0 + 0.65 * min(len(distinct_pos), 8) - 1.0 * neg_count
            score = round(max(2.0, min(9.5, raw)) / 10 * max_score, 1)

            evidence_bits = [s for s, _ in pos_hits if s not in negated][:2]
            if not evidence_bits:
                evidence_bits = [s for s, _ in neg_hits[:1]]
            evidence = (
                " ... ".join(b[:220] for b in evidence_bits)
                if evidence_bits
                else "No supporting evidence found in proposal."
            )
            pos_terms = sorted({k for _, m in pos_hits for k in m})
            neg_terms = sorted({k for _, m in neg_hits for k in m})
            justification = (
                f"Found {len(pos_hits)} supporting passage(s)"
                + (f" mentioning {', '.join(pos_terms[:5])}" if pos_terms else "")
                + (f"; {len(neg_hits)} concern(s) noted ({', '.join(neg_terms[:5])})" if neg_terms else "")
                + f". Score {score}/{max_score:g} reflects the balance of demonstrated strength "
                f"versus gaps on '{c['name']}'."
            )
            out_criteria.append(
                {
                    "criterion_id": c["criterion_id"],
                    "score": score,
                    "max_score": c["max_score"],
                    "justification": justification,
                    "evidence": evidence,
                }
            )
            for s, matched in neg_hits[:2]:
                risks.append(
                    f"{c['name']}: '{matched[0]}' - {s[:140].rstrip()}"
                )

        avg = (
            sum(x["score"] / float(x["max_score"]) for x in out_criteria) / len(out_criteria)
            if out_criteria
            else 0.0
        )
        return {
            "supplier_name": supplier_name,
            "criteria": out_criteria,
            "risks": risks[:6],
            "overall_summary": (
                f"Mock evaluation of {supplier_name}: average normalized criterion "
                f"performance {avg:.0%}. {len(risks)} risk/gap note(s) recorded. "
                "Scores are keyword-evidence based and fully deterministic."
            ),
        }


def get_client(provider: str = "mock", **kwargs: Any) -> BaseLLMClient:
    """Factory: provider='mock' or provider='openai' (any OpenAI-compatible API)."""
    provider = provider.lower().strip()
    if provider == "mock":
        return MockLLMClient()
    if provider in ("openai", "openai-compatible", "ollama", "openrouter"):
        return OpenAICompatibleClient(
            api_key=kwargs.get("api_key", ""),
            model=kwargs.get("model", "gpt-4o-mini"),
            base_url=kwargs.get("base_url"),
            timeout=float(kwargs.get("timeout", 120.0)),
        )
    raise LLMError(f"Unknown LLM provider: {provider!r}")
