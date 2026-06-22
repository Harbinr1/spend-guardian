from typing import Any, Dict, List
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
    # ------------------------------------------------------------
    # 1. Ingestion
    # ------------------------------------------------------------
    ingestion_result = ingest_transactions(input_data)
    raw_transactions = ingestion_result["transactions"]
    # Build the first piece of state
    state = {
        "transactions": raw_transactions,   # keep raw for later
        "vendor_matches": None,
        "waste_flags": None,
        "savings_reports": None,
    }
    
    # Validate that we actually got transactions
    assert len(raw_transactions) > 0, "❌ Ingestion produced zero transactions. Check your file format."
    
    # Convert to Pydantic models for type safety (optional but good)
    transactions = [Transaction(**t) for t in raw_transactions]
    
    # ------------------------------------------------------------
    # 2. Classification
    # ------------------------------------------------------------
    classification_result = classify_transactions({"transactions": raw_transactions})
    vendor_matches_raw = classification_result["vendor_matches"]
    vendor_matches = [VendorMatch(**vm) for vm in vendor_matches_raw]
    
    # Validate that we have exactly one match per transaction
    assert len(vendor_matches) == len(raw_transactions), \
        f"❌ Classification produced {len(vendor_matches)} matches for {len(raw_transactions)} transactions. Missing matches!"
    
    # Update state
    state["vendor_matches"] = vendor_matches_raw  # keep raw for serialization
    
    # ------------------------------------------------------------
    # 3. Waste Detection
    # ------------------------------------------------------------
    waste_input = {
        "transactions": raw_transactions,
        "vendor_matches": vendor_matches_raw
    }
    waste_result = detect_waste(waste_input)
    waste_flags_raw = waste_result["waste_flags"]
    waste_flags = [WasteFlag(**wf) for wf in waste_flags_raw]
    
    # Hard guardrail: every flag must require human review
    for flag in waste_flags:
        assert flag.requires_human_review is True, \
            f"❌ Guardrail violation: Flag {flag.flag_id} has requires_human_review=False"
    
    # Update state
    state["waste_flags"] = waste_flags_raw
    
    # ------------------------------------------------------------
    # 4. Recommendation (skip LLM call if no flags)
    # ------------------------------------------------------------
    if waste_flags:
        rec_input = {
            "waste_flags": waste_flags_raw,
            "transactions": raw_transactions
        }
        rec_result = generate_recommendations(rec_input)
        savings_reports_raw = rec_result["savings_reports"]
        savings_reports = [SavingsReport(**sr) for sr in savings_reports_raw]

        # Validate that we have one report per flag
        assert len(savings_reports) == len(waste_flags), \
            f"❌ Recommendation reports count mismatch: {len(savings_reports)} reports for {len(waste_flags)} flags."
    else:
        savings_reports_raw = []
        savings_reports = []

    # Update state
    state["savings_reports"] = savings_reports_raw
    
    # ------------------------------------------------------------
    # Build the final typed PipelineState
    # ------------------------------------------------------------
    final_state = PipelineState(
        transactions=transactions,
        vendor_matches=vendor_matches,
        waste_flags=waste_flags,
        savings_reports=savings_reports,
    )
    return final_state