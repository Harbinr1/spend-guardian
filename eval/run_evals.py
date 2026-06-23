"""
Run the pipeline against golden_cases and assert against EXPECTED.

Exit non-zero on failure so this can run before every demo rehearsal — you
want the Figma/Adobe failure mode to show up here, not live in front of
judges.
"""
import sys

from eval.golden_cases import GOLDEN_TRANSACTIONS, EXPECTED
from pipeline.adk_orchestrator import run_pipeline_adk as run_pipeline


# ---------------------------------------------------------------------------
# Ingestion unit tests (do NOT touch golden_cases.py)
# ---------------------------------------------------------------------------

def test_ingestion_malformed_row() -> list:
    """
    Feed ingestion a mixed list: one valid row and one with amount='N/A'.
    The malformed row must be skipped silently; the valid row must survive.
    This is the coverage for the skip-and-log path exercised in the demo.
    """
    from agents.ingestion import run as ingest

    rows = [
        # Valid row
        {"date": "2026-01-06", "raw_description": "AWS WEB SERVICES",
         "amount": 312.40, "currency": "CHF"},
        # Malformed row — amount cannot be coerced to float
        {"date": "2026-01-09", "raw_description": "SLACK TECHNOLOGIES",
         "amount": "N/A", "currency": "CHF"},
    ]

    failures = []
    result = ingest(rows)
    txns = result["transactions"]

    if len(txns) != 1:
        failures.append(
            f"Ingestion malformed-row: expected 1 transaction after skipping "
            f"malformed row, got {len(txns)}."
        )
    elif txns[0]["raw_description"] != "AWS WEB SERVICES":
        failures.append(
            f"Ingestion malformed-row: surviving transaction has wrong "
            f"description '{txns[0]['raw_description']}', expected 'AWS WEB SERVICES'."
        )
    elif txns[0]["amount"] != 312.40:
        failures.append(
            f"Ingestion malformed-row: surviving transaction has wrong "
            f"amount {txns[0]['amount']}, expected 312.40."
        )

    return failures


def test_ingestion_card_redaction() -> list:
    """
    Feed ingestion a row whose raw_description contains a credit-card number.
    The output must have the number replaced with XXXX-XXXX-XXXX-XXXX.
    """
    from agents.ingestion import run as ingest

    rows = [
        {"date": "2026-01-08",
         "raw_description": "NOTION LABS INC CARD 4242424242424242",
         "amount": 18.00, "currency": "CHF"},
    ]

    failures = []
    result = ingest(rows)
    txns = result["transactions"]

    if not txns:
        failures.append("Card redaction: ingestion returned zero transactions.")
    elif "4242424242424242" in txns[0]["raw_description"]:
        failures.append(
            "Card redaction: raw card number survived ingestion — "
            f"description is '{txns[0]['raw_description']}'."
        )
    elif "XXXX-XXXX-XXXX-XXXX" not in txns[0]["raw_description"]:
        failures.append(
            "Card redaction: expected 'XXXX-XXXX-XXXX-XXXX' in description, "
            f"got '{txns[0]['raw_description']}'."
        )

    return failures


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main() -> int:
    failures = []

    # --- Pipeline golden cases ---
    state = run_pipeline(GOLDEN_TRANSACTIONS)

    # Exact duplicate check
    duplicates = [f for f in state.waste_flags if f.overlap_category == "exact_duplicate"]
    if EXPECTED["duplicate_charge_flagged"] and not duplicates:
        failures.append("Expected an exact-duplicate charge to be flagged, none found.")

    # Normal recurrence must NOT be flagged as exact duplicate
    if EXPECTED.get("normal_recurrence_not_flagged"):
        normal_txn_ids = {"t7"}  # the recurrence in golden cases
        for f in duplicates:
            if any(tid in normal_txn_ids for tid in f.transaction_ids):
                failures.append(
                    f"Normal monthly recurrence was flagged as exact duplicate: {f.transaction_ids}"
                )

    # Category overlap guardrails
    overlaps = [f for f in state.waste_flags if f.overlap_category != "exact_duplicate"]
    for f in overlaps:
        if f.confidence_score.value == "high":
            failures.append(
                f"Category overlap for {f.vendor_name} was marked HIGH confidence — "
                f"category overlap alone must never exceed MEDIUM."
            )
        if not f.requires_human_review:
            failures.append(
                f"{f.vendor_name} overlap flag has requires_human_review=False — "
                f"must always be True."
            )

    # --- Ingestion unit tests ---
    failures += test_ingestion_malformed_row()
    failures += test_ingestion_card_redaction()

    if failures:
        print("EVAL FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    total = len(GOLDEN_TRANSACTIONS) + 2  # +2 for the ingestion unit tests
    print(
        f"All {total} cases passed "
        f"({len(GOLDEN_TRANSACTIONS)} golden pipeline + 2 ingestion unit tests)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())