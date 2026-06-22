Classification Agent

Role

Maps each Transaction to a VendorMatch (vendor name + category) using a
two-tier resolution:


Rule-based dictionary lookup (deterministic) — handles all known vendors.
LLM fallback (LOW tier) — only for vendor names not in the dictionary.


Input

list[Transaction]

Output

list[VendorMatch]

Model tier

DETERMINISTIC for dictionary hits. LOW tier for fallback only. Track what
fraction of transactions hit the fallback path — if it's high, grow the
dictionary instead of leaning harder on the model.

Guardrails


match_method must always be set ("rule_lookup" or "llm_fallback") so
fallback usage is auditable later.
LLM fallback output must validate against VendorMatch. On validation
failure, retry once with the validation error appended to the prompt, then
hard-fail loudly — never let a malformed result pass through silently.


Eval criteria


All golden-case known vendors (Figma, Adobe, Jira, Asana, AWS) resolve via
rule_lookup, not llm_fallback. If any of these fall through to the
model, the dictionary is missing an entry — fix the dictionary, not the
prompt.