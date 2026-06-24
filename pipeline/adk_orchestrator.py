"""
ADK‑based pipeline orchestrator.
Runs ingestion → classification → waste detection → recommendation.
Returns a dict with "state" (PipelineState) and "warnings" (list).
"""
from typing import Any, Dict

from schemas.models import (
    PipelineState, Transaction, VendorMatch, WasteFlag, SavingsReport,
)
from agents.adk_agents import (
    ingest_transactions,
    classify_transactions,
    detect_waste,
    generate_recommendations,
)
from mcp.progress import set_progress, clear_progress


def run_pipeline_adk(input_data: Any) -> Dict[str, Any]:
    try:
        set_progress("ingestion")
        ingestion_result = ingest_transactions(input_data)
        raw_transactions = ingestion_result["transactions"]
        warnings = ingestion_result.get("warnings", [])
        transactions = [Transaction(**t) for t in raw_transactions]

        set_progress("classification")
        classification_result = classify_transactions({"transactions": raw_transactions})
        vendor_matches = [VendorMatch(**vm) for vm in classification_result["vendor_matches"]]

        set_progress("waste_detection")
        waste_input = {
            "transactions": raw_transactions,
            "vendor_matches": classification_result["vendor_matches"]
        }
        waste_result = detect_waste(waste_input)
        waste_flags = [WasteFlag(**wf) for wf in waste_result["waste_flags"]]

        set_progress("recommendation")
        if waste_flags:
            rec_input = {
                "waste_flags": waste_result["waste_flags"],
                "transactions": raw_transactions
            }
            rec_result = generate_recommendations(rec_input)
            savings_reports = [SavingsReport(**sr) for sr in rec_result["savings_reports"]]
        else:
            savings_reports = []

        set_progress("complete")

        state = PipelineState(
            transactions=transactions,
            vendor_matches=vendor_matches,
            waste_flags=waste_flags,
            savings_reports=savings_reports,
        )
        return {"state": state, "warnings": warnings}
    finally:
        clear_progress()