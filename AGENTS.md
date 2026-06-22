# Spend Guardian — Agent Rules

## Tech stack
Python, Google ADK, LiteLLM (routed to Groq — Gemini API is regionally
restricted for this developer), FastAPI, Pydantic, React/Vite frontend.

## Do not touch without explicit instruction
- schemas/models.py
- agents/*.md (these are contracts, not drafts — implement against them,
  don't rewrite them)
- eval/golden_cases.py
- routing/model_router.py
- data/ (test fixtures — do not regenerate or overwrite)
## Safety guardrails (non-negotiable, see agents/waste_detection.md and
## agents/action.md for full detail)
- The waste-detection agent may only mark confidence_score=HIGH for an
  exact duplicate charge. Category overlap (e.g. two design tools) is
  capped at MEDIUM and always requires_human_review=True.
- The action agent never sends or cancels anything directly. It produces
  a draft only. Sending/cancelling requires a separate, explicit human
  approval step in api/main.py or cli/audit.py — never inside the agent
  pipeline itself.

## Before writing any agent's prompt logic
Restate in one sentence what that agent is and is not allowed to
conclude, based on its corresponding agents/*.md file.

## Testing requirements
Run python eval/run_evals.py after any change to waste_detection.py or
action.py. All golden cases must pass before considering the change done.