from typing import Any

from schemas.models import PipelineState, Transaction, VendorMatch, WasteFlag, SavingsReport
from agents.adk_agents import (
    ingest_transactions,
    classify_transactions,
    detect_waste,
    generate_recommendations
)

def run_pipeline_adk(input_data: Any) -> PipelineState:
    """
    Accept raw transactions and run the ADK agents sequentially:
    Ingestion -> Classification -> Waste Detection -> Recommendation
    """
    # 1. Ingestion
    ingestion_result = ingest_transactions(input_data)
    raw_transactions = ingestion_result["transactions"]
    transactions = [Transaction(**t) for t in raw_transactions]

    # 2. Classification
    classification_result = classify_transactions({"transactions": raw_transactions})
    vendor_matches = [VendorMatch(**vm) for vm in classification_result["vendor_matches"]]

    # 3. Waste Detection
    waste_input = {
        "transactions": raw_transactions,
        "vendor_matches": classification_result["vendor_matches"]
    }
    waste_result = detect_waste(waste_input)
    waste_flags = [WasteFlag(**wf) for wf in waste_result["waste_flags"]]

    # 4. Recommendation
    rec_input = {
        "waste_flags": waste_result["waste_flags"],
        "transactions": raw_transactions
    }
    rec_result = generate_recommendations(rec_input)
    savings_reports = [SavingsReport(**sr) for sr in rec_result["savings_reports"]]

    state = PipelineState(
        transactions=transactions,
        vendor_matches=vendor_matches,
        waste_flags=waste_flags,
        savings_reports=savings_reports,
    )
    return state
