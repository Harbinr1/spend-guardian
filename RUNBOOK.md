# Spend Guardian — Build Runbook

This document is self-contained. Paste it in full to any LLM session and it
should have everything needed to continue the build correctly, with no
other context required.

## 1. What this is

A 5-agent ADK pipeline (Ingestion → Classification → Waste Detection →
Recommendation → Action) that audits bank/credit-card statements to find
wasted SaaS subscription spend, and produces draft cancellation/downgrade
outreach for human approval. Built for a Kaggle x Google "Agents for
Business" hackathon. Stack: Python, Google ADK, LiteLLM routed to Groq,
FastAPI, Pydantic, React/Vite frontend (functional, connected to API).

## 2. Hard rules — apply to every file, no exceptions

1. Every `WasteFlag` has `requires_human_review = True`, with zero
   exceptions, including exact-duplicate charges. No flag ever skips
   review.
2. Category overlap (e.g. two design tools) is capped at
   `confidence_score = MEDIUM`. Only an exact duplicate charge (same
   vendor, same amount, **within 3 days**) may reach `HIGH`.
3. Same vendor/amount **28–31 days apart is a normal monthly recurrence,
   not a duplicate** — must produce zero flag, not a low-confidence one.
4. The Action agent only ever produces a draft (`status = DRAFTED`). It
   has no send/cancel tool in its available tool list, structurally, not
   just by prompt instruction. Sending/cancelling requires a separate,
   explicit human-approval step in `api/main.py` or `cli/audit.py`.
5. Never fabricate a judgment with no evidence. Bank transaction data has
   no usage/login signal — do not build "dormant" or "low utilization"
   detection on this data source. If you don't have the evidence, don't
   make the claim; flag for human review instead.
6. All monetary totals (`monthly_cost`, savings totals) are computed in
   code from actual transaction amounts — never asserted or computed by
   an LLM. This prevents silent arithmetic drift between runs.
7. Schema validation happens at every agent boundary. On a malformed LLM
   response, retry once with the validation error appended to the prompt;
   if it fails again, hard-fail loudly — never let bad data pass through
   silently.
8. Do not add a new pipeline stage/agent without explicit instruction.
   "Enrichment," "taxonomy.json," "dormancy detection," "owner/department
   fields," multi-source ingestion, caching, observability dashboards, and
   plugin systems are all explicitly OUT OF SCOPE for this build (see
   Section 8). If asked "should we add X for maintainability," the answer
   is no unless it's in the "still to do" list in Section 6.

## 3. Status as of this writing

- `schemas/models.py` — DONE and locked.
- `agents/ingestion.py` — DONE, sandbox-tested, working. Handles CSV
  string, dict-with-csv_data, or a bare list of row dicts. Redacts
  13–19-digit card-shaped sequences. Logs and skips malformed rows.
  Returns a `warnings` list alongside transactions.
- `agents/classification.py` — DONE. Rule dictionary first, LLM fallback
  second. In-memory cache for repeated unknown vendors. Retry once, then
  hard‑fail. Uses `match_method` and `match_confidence`.
- `agents/waste_detection.py` — DONE, sandbox‑tested, eval‑verified.
  Exact duplicates use date‑clustering to explicitly exclude normal
  monthly recurrences. Category overlap uses a single batched MEDIUM‑tier
  LLM call, capped at MEDIUM confidence. Named‑seat detection is
  deterministic. Monthly cost computed in code.
- `agents/recommendation.py` — DONE, sandbox‑tested. HIGH‑tier model
  writes action/reasoning; `potential_savings` from flag, never LLM.
  Retry + hard‑fail on malformed output.
- `agents/action.py` — DONE, sandbox‑tested. Always produces
  status=DRAFTED; no send/cancel tools. Retry + hard‑fail.
- `pipeline/orchestrator.py` — DONE (original, non‑ADK). Runs ingestion →
  classification → waste detection → recommendation. Action excluded.
- `pipeline/adk_orchestrator.py` — DONE (ADK‑based pipeline, identical
  sequence). Returns dict with `state` and `warnings`. Writes progress
  stages via `mcp/progress.py` for live overlay.
- `mcp/gmail_client.py` — DONE (mock draft logger with separate
  `create_draft()` and `send_draft()`).
- `mcp/draft_store.py` — DONE (shared draft storage helpers).
- `mcp/progress.py` — DONE (writes/reads/clears pipeline stage to
  `runs/progress.json`; stages: ingestion, classification,
  waste_detection, recommendation, complete).
- `mcp/action_agent.py` — DONE (formatted Slack message builder).
- `mcp/slack_client.py` — DONE (real Slack notification via webhook).
- `mcp/audit_log.py` — DONE (optional audit event logging).
- `api/main.py` — DONE (thin FastAPI wrapper; endpoints: `/audit`,
  `/audit/sample`, `/audit/upload`, `/audit/progress`, `/flags`,
  `/drafts`, `/draft`, `/approve`; CORS enabled; progress stub returns
  `{"stage": "idle"}`; real progress file used by orchestrator but not
  polled by frontend).
- `cli/audit.py` — DONE (CLI with `audit`, `list-flags`, `list-drafts`,
  `draft`, `approve` commands; persists state to `runs/last_audit.json`).
- `data/sample_transactions.json` — DONE, includes one intentionally
  malformed row (Slack with amount="N/A") to verify ingestion's skip
  behaviour.
- `eval/golden_cases.py`, `eval/run_evals.py` — DONE. Normal‑recurrence
  case added, all hard‑rule checks passing (9 cases: 7 golden pipeline
  + 2 ingestion unit tests).
- `agents/adk_agents.py` — DONE (ADK Agent wrappers for all five agents).
- `frontend/` — DONE (React/Vite dashboard with bento‑grid, dark theme,
  responsive design, CSV upload, live warning banner, timed audit
  progress overlay with AI model badges, Slack send button).
- `RUNBOOK.md` — this document.
- `AGENTS.md` — exists, contains the "do not touch" file list and core
  guardrails.

## 4. Files that are locked — do not modify without explicit instruction

- `schemas/models.py`
- `agents/*.md` (the five contract files)
- `eval/golden_cases.py`
- `routing/model_router.py`
- `data/` (test fixtures — treat any unrequested change as a bug)
- `frontend/`

## 5. Locked schema — schemas/models.py

```python
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionStatus(str, Enum):
    DRAFTED = "DRAFTED"
    APPROVED = "APPROVED"
    SENT = "SENT"


class Transaction(BaseModel):
    transaction_id: str
    date: str
    raw_description: str
    amount: float
    currency: str = "CHF"


class VendorMatch(BaseModel):
    """Output of the Classification agent — one per transaction."""
    transaction_id: str
    vendor_name: str
    category: str
    match_method: str  # "rule_lookup" | "llm_fallback"
    match_confidence: Confidence


class WasteFlag(BaseModel):
    flag_id: str
    vendor_name: str
    overlap_category: str  # e.g. "exact_duplicate" | "category_overlap" | "named_seat_ownership_unclear"
    confidence_score: Confidence
    requires_human_review: bool = True
    reason: str
    transaction_ids: List[str]
    monthly_cost: float


class SavingsReport(BaseModel):
    report_id: str
    flag_id: str
    action: str
    reasoning: str
    potential_savings: float


class ActionDraft(BaseModel):
    draft_id: str
    flag_id: str
    recipient: str
    subject: str
    body: str
    status: ActionStatus = ActionStatus.DRAFTED


class PipelineState(BaseModel):
    transactions: List[Transaction] = []
    vendor_matches: List[VendorMatch] = []
    waste_flags: List[WasteFlag] = []
    savings_reports: List[SavingsReport] = []
    action_drafts: List[ActionDraft] = []