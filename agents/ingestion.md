Ingestion Agent

Role

Parses raw bank/credit-card statement rows into validated Transaction
objects. This stage is deterministic — no LLM call. CSV parsing and field
normalization only.

Input

Raw CSV rows (date, description, amount, currency).

Output

list[Transaction] (see schemas/models.py)

Model tier

DETERMINISTIC — pure code. If statement formats vary enough that parsing
starts needing judgment calls, that's a signal to add another rule-based
format detector, not to reach for a model.

Guardrails


Redact any 13–19 digit sequences (card-number-shaped) in raw_description
before this data is stored anywhere persistent or passed to any model.
Never persist the original unredacted statement file after parsing.


Eval criteria


100% of well-formed rows produce a valid Transaction.
Malformed rows are logged and skipped — never silently dropped without a
log line.


Known failure mode

Different banks format statements differently. Build format detection rule
by rule as you encounter real formats. Don't try to generalize to every bank
up front — that's scope you don't have in 17 days.