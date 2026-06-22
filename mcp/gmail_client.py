"""
Mock Gmail client — logs drafts and sends to a local file/console.
Simulates draft creation and sending without real OAuth or API calls.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


DRAFTS_FILE = Path("runs/drafts.jsonl")


def create_draft(action_draft: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate creating a Gmail draft. Writes the draft to a JSONL file
    and prints it to stdout. Returns a simulated response.
    """
    draft_payload = {
        "draft_id": action_draft.get("draft_id", "unknown"),
        "flag_id": action_draft.get("flag_id", "unknown"),
        "recipient": action_draft.get("recipient", "unknown"),
        "subject": action_draft.get("subject", ""),
        "body": action_draft.get("body", ""),
        "status": action_draft.get("status", "DRAFTED"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    DRAFTS_FILE.parent.mkdir(exist_ok=True)
    with open(DRAFTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(draft_payload) + "\n")

    print("\n[MOCK GMAIL] Draft created:")
    print(f"  To: {draft_payload['recipient']}")
    print(f"  Subject: {draft_payload['subject']}")
    print(f"  Body: {draft_payload['body'][:100]}...")
    print(f"  Status: {draft_payload['status']}")
    print(f"  Logged to: {DRAFTS_FILE}")

    return {
        "success": True,
        "message": "Draft created (mock). No email sent.",
        "draft_id": draft_payload["draft_id"],
    }


def send_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate sending a draft. Appends a new entry with status 'SENT'.
    Does not duplicate the original draft.
    """
    sent_entry = {
        **draft,
        "status": "SENT",
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    DRAFTS_FILE.parent.mkdir(exist_ok=True)
    with open(DRAFTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(sent_entry) + "\n")

    print(f"\n[MOCK GMAIL] Draft sent (mock): {sent_entry['draft_id']}")
    return {"success": True, "message": "Draft sent (mock).", "draft_id": draft["draft_id"]}