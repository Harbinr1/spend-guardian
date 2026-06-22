"""
CLI for Spend Guardian. Same functionality as the API.
No duplicated pipeline logic (uses shared orchestrator and draft store).
"""
import argparse
import json
from pathlib import Path

from pipeline.adk_orchestrator import run_pipeline_adk as run_pipeline
from mcp.gmail_client import create_draft, send_draft
from mcp.draft_store import read_all_drafts, update_draft_status
from agents.action import run as run_action
from schemas.models import PipelineState

LAST_AUDIT_FILE = Path("runs/last_audit.json")


def _save_state(state: PipelineState):
    LAST_AUDIT_FILE.parent.mkdir(exist_ok=True)
    data = {
        "transactions": [t.model_dump() for t in state.transactions],
        "vendor_matches": [v.model_dump() for v in state.vendor_matches],
        "waste_flags": [f.model_dump() for f in state.waste_flags],
        "savings_reports": [r.model_dump() for r in state.savings_reports],
    }
    with open(LAST_AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _load_last_state():
    if not LAST_AUDIT_FILE.exists():
        return None
    with open(LAST_AUDIT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Reconstruct PipelineState from the saved dicts
    from schemas.models import Transaction, VendorMatch, WasteFlag, SavingsReport
    return PipelineState(
        transactions=[Transaction(**t) for t in data.get("transactions", [])],
        vendor_matches=[VendorMatch(**v) for v in data.get("vendor_matches", [])],
        waste_flags=[WasteFlag(**w) for w in data.get("waste_flags", [])],
        savings_reports=[SavingsReport(**s) for s in data.get("savings_reports", [])],
    )


def cmd_audit(args):
    data = json.loads(Path(args.input).read_text())
    state = run_pipeline(data)
    _save_state(state)
    # Also print the result
    result = {
        "transactions": [t.model_dump() for t in state.transactions],
        "vendor_matches": [v.model_dump() for v in state.vendor_matches],
        "waste_flags": [f.model_dump() for f in state.waste_flags],
        "savings_reports": [r.model_dump() for r in state.savings_reports],
    }
    print(json.dumps(result, indent=2, default=str))


def cmd_list_flags(args):
    state = _load_last_state()
    if state is None:
        print("No audit data. Run 'audit' first.")
        return
    flags = [f.model_dump() for f in state.waste_flags]
    print(json.dumps(flags, indent=2, default=str))


def cmd_list_drafts(args):
    drafts = read_all_drafts()
    if not drafts:
        print("No drafts yet.")
        return
    for d in drafts:
        print(json.dumps(d, indent=2, default=str))


def cmd_draft(args):
    """Trigger Action agent for a specific flag and store the draft."""
    state = _load_last_state()
    if state is None:
        print("No audit data. Run 'audit' first.")
        return
    flag = None
    for f in state.waste_flags:
        if f.flag_id == args.flag_id:
            flag = f
            break
    if flag is None:
        print(f"Flag {args.flag_id} not found.")
        return

    result = run_action({
        "waste_flag": flag.model_dump(),
        "recipient": args.recipient,
    })
    draft = result["action_draft"]
    create_draft(draft)
    print(json.dumps(draft, indent=2, default=str))


def cmd_approve(args):
    draft_id = args.draft_id
    updated = update_draft_status(draft_id, "APPROVED")
    if not updated:
        print(f"Draft {draft_id} not found.")
        return

    # 1. Find the flag_id from the draft
    all_drafts = read_all_drafts()
    draft = next((d for d in all_drafts if d.get("draft_id") == draft_id), None)
    if draft is None:
        print(f"Draft {draft_id} found in status update but not in full list. Aborting.")
        return
    
    flag_id = draft.get("flag_id")
    if not flag_id:
        print(f"Draft {draft_id} has no flag_id. Aborting.")
        return

    # 2. Load the last audit state to get the actual savings report
    state = _load_last_state()
    if state is None:
        print("No audit data found. Run 'audit' first.")
        return

    # 3. Find the matching savings report
    report = next((r for r in state.savings_reports if r.flag_id == flag_id), None)
    if report is None:
        print(f"No savings report found for flag_id: {flag_id}")
        return

    # 4. Post to Slack with REAL data from the report
    from mcp.action_agent import post_draft_to_slack
    result = post_draft_to_slack(
        flag_id=flag_id,
        action=report.action,
        reasoning=report.reasoning,
        potential_savings=report.potential_savings
    )

    from mcp.audit_log import log_audit_entry

    log_audit_entry("draft_approved", {
        "draft_id": draft_id,
        "flag_id": flag_id,
        "action": report.action,
        "savings": report.potential_savings
    })

    # Optionally mark as SENT in draft store
    update_draft_status(draft_id, "SENT")

    print(f"[OK] Draft {draft_id} approved and posted to Slack. Status: {result['status']}")

def main():
    parser = argparse.ArgumentParser(prog="spendguardian", description="Spend Guardian CLI")
    sub = parser.add_subparsers(dest="command")

    p_audit = sub.add_parser("audit", help="Run full audit on a transactions file")
    p_audit.add_argument("input", help="Path to JSON transactions file")

    
    sub.add_parser("list-flags", help="List waste flags from last audit")
    sub.add_parser("list-drafts", help="List saved drafts")

    p_draft = sub.add_parser("draft", help="Generate an outreach draft for a specific flag")
    p_draft.add_argument("flag_id", help="Waste flag ID to draft for")
    p_draft.add_argument("--recipient", default="finance@example.com", help="Recipient email")
    

    p_approve = sub.add_parser("approve", help="Approve and send a draft")
    p_approve.add_argument("draft_id", help="Draft ID to approve")

    args = parser.parse_args()
    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "list-flags":
        cmd_list_flags(args)
    elif args.command == "list-drafts":
        cmd_list_drafts(args)
    elif args.command == "draft":
        cmd_draft(args)
    elif args.command == "approve":
        cmd_approve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()