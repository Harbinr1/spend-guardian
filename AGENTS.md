# Spend Guardian — Agent Rules

## Tech stack
Python, Google ADK, LiteLLM (routed to Groq — Gemini API is regionally
restricted for this developer), FastAPI, Pydantic, React/Vite frontend.

## Do not touch without explicit instruction
- schemas/models.py
- agents/*.md (contracts, not drafts — implement against them)
- eval/golden_cases.py
- routing/model_router.py
- data/ (test fixtures — do not regenerate or overwrite)
- FRONTEND_SPEC.md (contract for the frontend, same rule as agents/*.md)

## Canonical orchestrator
`pipeline/adk_orchestrator.py` is the orchestrator used by the API, CLI,
and eval suite. It includes state assertions after every stage and the
audit-logging integration. Do not build against or revive the older
vanilla `pipeline/orchestrator.py`.

## Safety guardrails (non-negotiable — see agents/waste_detection.md and
## agents/action.md for full detail)
- The waste-detection agent may only mark confidence_score=HIGH for an
  exact duplicate charge (same vendor, same amount, within 3 days).
  Category overlap is capped at MEDIUM and always
  requires_human_review=True, with zero exceptions.
- The action agent never sends or posts anything directly. It produces a
  draft only (status=DRAFTED). The actual Slack notification (via
  mcp/action_agent.py, posting to SLACK_WEBHOOK_URL) only happens after
  an explicit human approval step in api/main.py or cli/audit.py — never
  inside the agent pipeline itself.
- Every critical event (ingestion errors, draft approvals) is logged via
  mcp/audit_log.py to an immutable, append-only log. Don't bypass this
  logging when adding new actions.

## Frontend work
frontend/ is governed by FRONTEND_SPEC.md, not this file. The only
backend change a frontend-focused session may make is adding CORS
middleware to api/main.py — no new endpoints, no business logic in the
UI.

## Before writing any agent's prompt logic
Restate in one sentence what that agent is and is not allowed to
conclude, based on its corresponding agents/*.md file.

## Testing requirements
Run python eval/run_evals.py after any change to waste_detection.py or
action.py. All golden cases must pass before considering the change
done.