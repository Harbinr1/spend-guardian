Waste-Detection Agent

Role

Identifies potential overlap/waste across VendorMatch entries and produces
WasteFlags. This is the agent doing actual reasoning, and the one with the
most important guardrail in the whole pipeline. Read this file twice before
touching the prompt.

Input

list[VendorMatch]

Output

list[WasteFlag]

Model tier

MEDIUM — this needs genuine reasoning (is this overlap meaningful, or not),
unlike ingestion/classification which are mostly lookups.

Guardrails — non-negotiable


We are reasoning from bank transaction data only. We do NOT know how a
team actually uses a tool. Figma and Adobe being in the same category is
NOT evidence they're redundant — Adobe might be used by marketing for
video, Figma by product for design. The agent has no way to know this from
a statement line, and must not pretend otherwise.
confidence_score may be HIGH only for an exact duplicate charge — same
vendor, same amount, billed twice. Category overlap alone is capped at
MEDIUM, never HIGH.
requires_human_review defaults to True for every flag, including exact
duplicates. No flag should ever skip human review.
reasoning must state the actual evidence ("same category, no usage data
available to confirm distinct use case") — never assert redundancy as
settled fact.


Eval criteria

Enforced in eval/run_evals.py as hard failures, not warnings:


Any category-overlap flag with confidence_score == HIGH fails the suite.
Any flag with requires_human_review == False fails the suite.