"""
Golden test cases for deterministic evaluation of the pipeline.

These are plain dicts (the same format the pipeline's first stage receives)
so they can be fed directly to the orchestrator.
"""

from schemas.models import Transaction
GOLDEN_TRANSACTIONS = [
    {"transaction_id": "t1", "date": "2026-01-03", "raw_description": "FIGMA INC", "amount": 45.00},
    {"transaction_id": "t2", "date": "2026-01-04", "raw_description": "ADOBE CREATIVE CLOUD", "amount": 59.99},
    {"transaction_id": "t3", "date": "2026-01-05", "raw_description": "JIRA SOFTWARE", "amount": 70.00},
    {"transaction_id": "t4", "date": "2026-01-05", "raw_description": "ASANA INC", "amount": 24.99},
    # Exact duplicate charges — same vendor, same amount, within 3 days
    {"transaction_id": "t5", "date": "2026-01-06", "raw_description": "AWS WEB SERVICES", "amount": 312.40},
    {"transaction_id": "t6", "date": "2026-01-06", "raw_description": "AWS WEB SERVICES", "amount": 312.40},
    # Normal monthly recurrence — same vendor, same amount, 30 days apart.
    # The pipeline must NOT flag this as waste.
    {"transaction_id": "t7", "date": "2026-02-05", "raw_description": "AWS WEB SERVICES", "amount": 312.40},
]

# What the pipeline must and must not conclude.
EXPECTED = {
    "duplicate_charge_flagged": True,
    "duplicate_charge_min_confidence": "high",
    # category overlap (Figma/Adobe, Jira/Asana) must never exceed MEDIUM
    # confidence, and must never skip human review — this is the core
    # safety guarantee for the whole pipeline.
    "category_overlap_max_confidence": "medium",
    "category_overlap_requires_review": True,
    # The normal recurrence (t7) must NOT produce a duplicate flag.
    "normal_recurrence_not_flagged": True,
}

