"""
Thin FastAPI wrapper around the orchestrator.
Only here can a draft move from DRAFTED → SENT (Hard Rule 4).
No duplicated pipeline logic with the CLI.
"""
import json
from pathlib import Path
from typing import Any, Dict, List
from mcp.progress import get_progress
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel

from pipeline.adk_orchestrator import run_pipeline_adk as run_pipeline
from mcp.gmail_client import create_draft, send_draft
from mcp.draft_store import read_all_drafts, update_draft_status, find_draft_by_id
from agents.action import run as run_action
from schemas.models import PipelineState

app = FastAPI(title="Spend Guardian")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In‑memory store of the last audit result (per process)
last_state: PipelineState | None = None

LAST_AUDIT_FILE = Path("runs/last_audit.json")


class AuditRequest(BaseModel):
    transactions: List[Dict[str, Any]]


class DraftRequest(BaseModel):
    flag_id: str
    recipient: str = "finance@example.com"


class ApprovalRequest(BaseModel):
    draft_id: str


def _save_to_file(state: PipelineState):
    """Save pipeline state to runs/last_audit.json so the frontend can read it."""
    LAST_AUDIT_FILE.parent.mkdir(exist_ok=True)
    data = _state_to_dict(state)
    with open(LAST_AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _state_to_dict(state: PipelineState):
    return {
        "transactions": [t.model_dump() for t in state.transactions],
        "vendor_matches": [v.model_dump() for v in state.vendor_matches],
        "waste_flags": [f.model_dump() for f in state.waste_flags],
        "savings_reports": [r.model_dump() for r in state.savings_reports],
    }


@app.post("/audit")
def run_audit(request: AuditRequest):
    """Run the full automatic pipeline (ingestion → recommendation)."""
    global last_state
    try:
        result = run_pipeline(request.transactions)          # dict with "state" and "warnings"
        state = result["state"]
        last_state = state
        _save_to_file(state)
        return _state_to_dict(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/sample")
def run_audit_sample():
    """Run the pipeline against the built-in sample transactions."""
    sample_path = Path("data/sample_transactions.json")
    if not sample_path.exists():
        raise HTTPException(status_code=500, detail="Sample data file not found.")
    try:
        sample_data = json.loads(sample_path.read_text())
        result = run_pipeline(sample_data)
        state = result["state"]
        global last_state
        last_state = state
        _save_to_file(state)
        return _state_to_dict(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a CSV bank statement, run the pipeline, and persist results."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read uploaded file.")
    finally:
        await file.close()
    if not content.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        csv_text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding must be UTF-8.")
    try:
        result = run_pipeline({"csv_data": csv_text})
        state = result["state"]
        global last_state
        last_state = state
        _save_to_file(state)
        return _state_to_dict(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@app.get("/audit/progress")
def audit_progress():
    return get_progress()


@app.get("/flags")
def list_flags():
    """Return waste flags from the last audit (if any)."""
    if last_state is not None:
        return {"waste_flags": [f.model_dump() for f in last_state.waste_flags]}
    if not LAST_AUDIT_FILE.exists():
        return {"waste_flags": [], "message": "No audit run yet."}
    with open(LAST_AUDIT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"waste_flags": data.get("waste_flags", [])}


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
    updated = update_draft_status(draft_id, "APPROVED")
    if not updated:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found.")
    result = send_draft(updated)
    return {"status": "SENT", "draft_id": draft_id, "message": result["message"]}