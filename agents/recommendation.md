Recommendation Agent

Role

Synthesizes all WasteFlags into a SavingsReport — the human-readable,
judge-facing output. This is the agent where output quality (clarity, tone,
trustworthiness of the framing) matters most for the demo.

Input

list[WasteFlag]

Output

SavingsReport

Model tier

HIGH — the one place where spending more on a better model is worth it,
since output quality directly drives how convincing the demo is.

Guardrails


The summary must distinguish between "confirmed duplicate charge" and
"flagged for review" — never present both with equal certainty.
total_monthly_waste_estimate is computed in code from each flag's
monthly_cost, never asserted by the model. Keep the headline number
trustworthy and re-derivable.


Eval criteria


The computed total exactly matches the sum of flagged monthly_cost
values (code-checked, not model-checked).