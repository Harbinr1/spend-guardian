Spend Guardian — Build Structure

Five-agent pipeline (ingestion → classification → waste-detection →
recommendation → action), deterministic wherever possible, LLM only where
reasoning is genuinely required. See routing/model_router.py for tiering
logic and agents/*.md for each agent's full contract — read these before
writing any agent code, not after.

Build order


schemas/models.py — lock this first. Every agent boundary validates
against it; nothing downstream is real until this is settled.
agents/ingestion.md → write agents/ingestion.py. Deterministic,
no model calls.
agents/classification.md → write agents/classification.py. Rule
dictionary first, LLM fallback second.
agents/waste_detection.md → write agents/waste_detection.py.
Read this file's guardrails twice before writing the prompt. This is
the agent that can embarrass you live if left unconstrained.
agents/recommendation.md, agents/action.md → the two HIGH-tier,
judge-facing/human-facing agents.
pipeline/orchestrator.py — wires all five with a state assertion after
every handoff (this is where you previously hit issues with edge formats
and session state — validate explicitly here, don't assume it works).
eval/run_evals.py — run this after every change to waste_detection.py
especially, and again before every demo rehearsal.


Testing an agent before it's wired into the pipeline

python sandbox/run_agent_sandbox.py classification --fixture data/sample_transactions.json

Running the eval suite

python eval/run_evals.py

This directly enforces the human-review safety guarantee discussed for
waste detection — a category-overlap flag marked HIGH confidence, or any
flag with requires_human_review=False, is a hard failure here, not a
warning you can ignore.

What's intentionally not built yet


pipeline/orchestrator.py — needs the five agent implementations first.
mcp/gmail_client.py (or Slack fallback) — wire this after the core
pipeline passes evals, not before. Test OAuth/auth failure cases
deliberately once you do.
api/main.py, frontend/ — thin layers over the orchestrator once it's
proven correct in isolation.