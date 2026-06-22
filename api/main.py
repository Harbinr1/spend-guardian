"""
Thin FastAPI wrapper around the orchestrator.
Only here can a draft move from DRAFTED → SENT (Hard Rule 4).
No duplicated pipeline logic with the CLI.
"""
import json
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pipeline.orchestrator import run_pipeline
from mcp.gmail_client import create_draft, send_draft
from mcp.draft_store import read_all_drafts, update_draft_status, find_draft_by_id
from agents.action import run as run_action
from schemas.models import PipelineState

app = FastAPI(title="Spend Guardian")

# In‑memory store of the last audit result (per process)
last_state: PipelineState | None = None


class AuditRequest(BaseModel):
    transactions: List[Dict[str, Any]]


class DraftRequest(BaseModel):
    flag_id: str
    recipient: str = "finance@example.com"


class ApprovalRequest(BaseModel):
    draft_id: str


@app.post("/audit")
def run_audit(request: AuditRequest):
    """Run the full automatic pipeline (ingestion → recommendation)."""
    global last_state
    try:
        state = run_pipeline(request.transactions)
        last_state = state
        return {
            "transactions": [t.model_dump() for t in state.transactions],
            "vendor_matches": [v.model_dump() for v in state.vendor_matches],
            "waste_flags": [f.model_dump() for f in state.waste_flags],
            "savings_reports": [r.model_dump() for r in state.savings_reports],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flags")
def list_flags():
    """Return waste flags from the last audit (if any)."""
    if last_state is None:
        return {"waste_flags": [], "message": "No audit run yet."}
    return {"waste_flags": [f.model_dump() for f in last_state.waste_flags]}


@app.get("/drafts")
def list_drafts():
    """Return all drafts from the mock drafts log as parsed objects."""
    drafts = read_all_drafts()
    return {"drafts": drafts}


@app.post("/draft")
def create_action_draft(req: DraftRequest):
    """
    Trigger the Action agent for a specific waste flag (human-selected).
    Creates an ActionDraft and stores it via the mock Gmail client.
    """
    if last_state is None:
        raise HTTPException(status_code=400, detail="No audit data. Run /audit first.")
    # Find the flag by flag_id
    flag = None
    for f in last_state.waste_flags:
        if f.flag_id == req.flag_id:
            flag = f
            break
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Flag {req.flag_id} not found.")

    try:
        action_result = run_action({
            "waste_flag": flag.model_dump(),
            "recipient": req.recipient,
        })
        draft_dict = action_result["action_draft"]
        # Store draft via mock Gmail
        create_draft(draft_dict)
        return draft_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve")
def approve_and_send(req: ApprovalRequest):
    """
    Move a draft from DRAFTED → APPROVED → SENT (mock send).
    This is the only place status moves past DRAFTED (Hard Rule 4).
    """
    draft_id = req.draft_id
    # Update status to APPROVED in the log (in place)
    updated = update_draft_status(draft_id, "APPROVED")
    if not updated:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found.")

    # Simulate sending (logs a separate sent entry)
    result = send_draft(updated)

    return {"status": "SENT", "draft_id": draft_id, "message": result["message"]}