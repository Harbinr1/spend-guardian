Action Agent

Role

Drafts an outreach message (cancellation/downgrade email, or a Slack message
to finance) for a WasteFlag a human has chosen to act on. This is the ONLY
agent with any path to an external system (Gmail/Slack MCP) — and even then,
only to create a draft.

Input

A single WasteFlag, selected by a human reviewer (never auto-selected by
the pipeline).

Output

ActionDraft with status = DRAFTED

Model tier

HIGH — written communication quality matters here, and call volume is low
(one per human-selected action, not one per transaction), so cost isn't a
real concern for this agent.

Guardrails — hard rule, not a suggestion


This agent never calls a send or cancel action directly. It only produces
a draft. Enforce this structurally: the actual MCP send/cancel tool must
not be in this agent's available tool list at all — don't rely on the
prompt alone to prevent this.
status only advances past DRAFTED via an explicit human approval call
in the API/CLI. The agent pipeline itself never changes this field again
after creating the draft.


Eval criteria


status is DRAFTED immediately after this agent runs, for every input,
with no exceptions.