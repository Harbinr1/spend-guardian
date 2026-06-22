"""
Run the pipeline against golden_cases and assert against EXPECTED.

Exit non-zero on failure so this can run before every demo rehearsal — you
want the Figma/Adobe failure mode to show up here, not live in front of
judges.
"""
import sys

from eval.golden_cases import GOLDEN_TRANSACTIONS, EXPECTED
from pipeline.orchestrator import run_pipeline


def main() -> int:
    state = run_pipeline(GOLDEN_TRANSACTIONS)
    failures: list[str] = []

    # --- Exact duplicate check ---
    duplicates = [f for f in state.waste_flags if f.overlap_category == "exact_duplicate"]
    if EXPECTED["duplicate_charge_flagged"] and not duplicates:
        failures.append("Expected an exact-duplicate charge to be flagged, none found.")

    # --- Normal recurrence must NOT be flagged as exact duplicate ---
    if EXPECTED.get("normal_recurrence_not_flagged"):
        normal_txn_ids = {"t7"}  # the recurrence in golden cases
        for f in duplicates:
            if any(tid in normal_txn_ids for tid in f.transaction_ids):
                failures.append(
                    f"Normal monthly recurrence was flagged as exact duplicate: {f.transaction_ids}"
                )

    # --- Category overlap guardrails ---
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

    if failures:
        print("EVAL FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(GOLDEN_TRANSACTIONS)} golden cases passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())