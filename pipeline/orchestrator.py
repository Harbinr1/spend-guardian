"""
Orchestrator — ingestion → classification → waste detection → recommendation.
Action is NOT part of the automatic sequence (triggered on human selection).
"""
from typing import Any, List

from schemas.models import (
    PipelineState, Transaction, VendorMatch, WasteFlag,
    SavingsReport,
)
from agents.ingestion import run as ingest
from agents.classification import run as classify
from agents.waste_detection import run as detect_waste
from agents.recommendation import run as recommend


def run_pipeline(input_data: Any) -> PipelineState:
    """Run the automatic pipeline stages and return a populated PipelineState."""

    # 1. Ingestion
    ingestion_result = ingest(input_data)
    raw_transactions = ingestion_result["transactions"]
    transactions = [Transaction(**t) for t in raw_transactions]

    # 2. Classification
    classification_result = classify({"transactions": raw_transactions})
    vendor_matches = [VendorMatch(**vm) for vm in classification_result["vendor_matches"]]

    # 3. Waste Detection
    waste_input = {
        "transactions": raw_transactions,
        "vendor_matches": classification_result["vendor_matches"]
    }
    waste_result = detect_waste(waste_input)
    waste_flags = [WasteFlag(**wf) for wf in waste_result["waste_flags"]]

    # 4. Recommendation
    if waste_flags:
        rec_input = {
            "waste_flags": waste_result["waste_flags"],
            "transactions": raw_transactions,
        }
        rec_result = recommend(rec_input)
        savings_reports = [SavingsReport(**sr) for sr in rec_result["savings_reports"]]
    else:
        savings_reports = []

    state = PipelineState(
        transactions=transactions,
        vendor_matches=vendor_matches,
        waste_flags=waste_flags,
        savings_reports=savings_reports,
    )
    return state