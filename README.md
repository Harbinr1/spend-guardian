# Spend Guardian

**AI‑powered SaaS subscription waste detection with human‑in‑the‑loop safety.**  
A 5‑agent ADK pipeline that audits bank statements to find duplicate charges, overlapping tools, and unclear ownership — then drafts cancellation/downgrade outreach for a human to approve and post to Slack. Never sends anything automatically.

Built for the Kaggle x Google "AI Agents: Intensive Vibe Coding" Capstone — **Agents for Business** track.

---

## The Problem

Businesses lose thousands on forgotten SaaS subscriptions. Tools like Figma, Adobe, Jira, and Asana get bought by different teams and billed to the same credit card without anyone noticing. Bank statements alone contain enough signal to catch duplicate charges and overlapping tools, but manual audits are slow and error‑prone.

---

## The Solution

Spend Guardian is a **multi‑agent pipeline** that:

1. **Ingests** messy bank export files (CSV, JSON, raw text).  
2. **Classifies** each transaction to a vendor and category using deterministic rules, with an LLM fallback for unknown vendors.  
3. **Detects waste** — exact duplicates within 3 days (HIGH confidence), category overlaps (MEDIUM confidence), and named‑seat ownership risks.  
4. **Recommends actions** — "Cancel duplicate," "Investigate further," etc. — with potential savings computed from actual amounts, never from the LLM.  
5. **Drafts outreach** — but never sends anything. A human must approve every draft via the CLI or API, which then posts to a private Slack channel.

**All monetary values are calculated in code; every flag requires human review; category overlaps never exceed MEDIUM confidence; and the Action agent has no ability to send anything.**

---

## Architecture

```
Bank Statement
│
▼
┌─────────────────┐
│ Ingestion       │ deterministic, no LLM
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Classification  │ rule dictionary → LOW‑tier LLM fallback
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Waste Detection │ MEDIUM‑tier LLM for category overlap only
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Recommendation  │ HIGH‑tier LLM for action/reasoning prose
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Human Review    │ ← CLI / API (only here can status move past DRAFTED)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Action (draft)  │ HIGH‑tier LLM — drafts only, structurally cannot send
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Slack Webhook   │ ← Posts approved draft to private Slack channel
└─────────────────┘
```

The canonical orchestrator is **`pipeline/adk_orchestrator.py`**, which wraps each agent as a `google.adk.Agent` with `FunctionTool`s and includes runtime assert guards at every agent boundary (including a Hard Rule 1 check that every flag has `requires_human_review=True`).

The automatic pipeline sequence is **Ingestion → Classification → Waste Detection → Recommendation**. The **Action agent is not automatic** — it's triggered by a human selecting a specific waste flag via the CLI or API.

---

## Safety Guardrails (Hard Rules)

1. Every `WasteFlag` has `requires_human_review = True` — **no exceptions**. Enforced by an `assert` in the orchestrator.
2. Category overlap is capped at `confidence_score = MEDIUM`. Only exact duplicate charges (same vendor, same amount, **within 3 days**) reach `HIGH`.
3. Same vendor/amount **28–31 days apart is a normal monthly recurrence, not a duplicate** — never flagged.
4. The Action agent **only drafts**. It has no send/cancel tool structurally. Only explicit human approval in `api/main.py` or `cli/audit.py` can move a draft past DRAFTED.
5. No dormancy or usage claims — bank data has no login signal.
6. All monetary totals (`monthly_cost`, `potential_savings`) are computed in code from transaction amounts, never by an LLM.
7. Schema validation at every agent boundary; retry once on malformed output, then hard‑fail.
8. No enrichment, taxonomy, or multi‑source ingestion — these are listed as future work.

An **eval suite** (`eval/run_evals.py`) enforces these rules against the ADK orchestrator. Any flag with `requires_human_review=False` or a category overlap marked `HIGH` **fails the eval immediately**.

---

## Course Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| **Agent / Multi‑agent system (ADK)** | Five agents defined as `google.adk.Agent` with `FunctionTool`s in `agents/adk_agents.py`; canonical orchestrator in `pipeline/adk_orchestrator.py` |
| **Security features** | Card number redaction in ingestion, `requires_human_review=True` everywhere (runtime assert), Action agent structurally blocked from sending |
| **Agent skills (CLI)** | Full CLI (`cli/audit.py`) with `audit`, `list‑flags`, `list‑drafts`, `draft`, and `approve` commands |
| **Audit logging** | `mcp/audit_log.py` logs every approval with flag ID, action, and savings to `runs/audit_log.json` |
| **External integration** | Approved drafts are posted to a private Slack channel via webhook (`mcp/action_agent.py`) |

---

## Quickstart

### Prerequisites
- Python 3.10+
- Groq API key (free tier works)
- (Optional) Slack incoming webhook URL for the approve flow

### Setup

```bash
git clone https://github.com/Harbinr1/spend-guardian.git
cd spend-guardian
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
MODEL_LOW=groq/openai/gpt-oss-20b
MODEL_MEDIUM=groq/openai/gpt-oss-20b
MODEL_HIGH=groq/openai/gpt-oss-120b
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL   # optional
```

### Run the Full Pipeline (CLI)

```bash
python -m cli.audit audit data/sample_transactions.json
```

This will:
- Ingest sample transactions (malformed rows are skipped with a warning)
- Classify vendors
- Flag exact duplicates (AWS, $312.40 billed twice within 3 days) and category overlaps (Design: Figma+Adobe; Project Management: Jira+Asana)
- Produce savings reports with potential savings calculated from actual amounts

### Generate a Draft (requires a previous audit)

```bash
python -m cli.audit draft exact_dup_AWS_312.4 --recipient finance@acme.com
```

### Approve and Post to Slack

```bash
python -m cli.audit approve draft_exact_dup_AWS_312.4
```

This approves the draft, posts it to the configured Slack channel (or prints a mock if `SLACK_WEBHOOK_URL` is not set), logs the approval to `runs/audit_log.json`, and marks the draft as SENT.

### Run the Eval Suite

```bash
python -m eval.run_evals
```

All 7 golden cases should pass (including the normal recurrence exclusion). The eval suite tests the canonical ADK orchestrator path.

### API (Optional)

Start the FastAPI server:

```bash
uvicorn api.main:app --reload
```

Then open http://127.0.0.1:8000/docs for interactive Swagger documentation.  
Endpoints: `POST /audit`, `GET /flags`, `GET /drafts`, `POST /draft`, `POST /approve`.

---

## Repository Structure

```
├── agents/               # Five agents + ADK wrappers (adk_agents.py) + contract docs (*.md)
├── pipeline/
│   ├── adk_orchestrator.py           # Canonical orchestrator (ADK, with assert guards)
│   └── orchestrator_deprecated.py    # Legacy vanilla orchestrator (reference only)
├── mcp/
│   ├── gmail_client.py       # Mock draft logger (writes to runs/drafts.jsonl)
│   ├── draft_store.py        # Draft CRUD (read, update status)
│   ├── action_agent.py       # Slack webhook integration (posts approved drafts)
│   └── audit_log.py          # Audit logging (writes to runs/audit_log.jsonl)
├── api/                  # FastAPI thin wrapper
├── cli/                  # CLI thin wrapper
├── schemas/              # Pydantic models (locked schema)
├── eval/                 # Golden cases + eval runner (tests ADK path)
├── data/                 # Sample transactions fixture
├── routing/              # Model tier routing (LOW/MEDIUM/HIGH)
├── sandbox/              # Agent sandbox test runner
├── RUNBOOK.md            # Full build runbook (source of truth for development)
├── AGENTS.md             # Agent contracts and locked file list
└── README.md             # This file
```

---

## Future Work

- `data/taxonomy.json` — central vendor dictionary
- Enrichment agent for monthly cost estimation, department inference
- Dormancy / utilization detection (requires login data, not just bank statements)
- Multi‑source ingestion (Stripe, Okta)
- Real Gmail OAuth integration
- Caching, rate limiting, observability

These are explicitly out of scope for the capstone but represent a natural production path.
