"""
Shared draft storage helpers. Used by API and CLI to avoid code duplication.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DRAFTS_FILE = Path("runs/drafts.jsonl")


def read_all_drafts() -> List[Dict[str, Any]]:
    """Return all parsed draft entries from the log file."""
    if not DRAFTS_FILE.exists():
        return []
    drafts = []
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                drafts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return drafts


def find_draft_by_id(draft_id: str) -> Optional[Dict[str, Any]]:
    """Find a draft by ID. Returns the parsed draft dict or None."""
    for d in read_all_drafts():
        if d.get("draft_id") == draft_id:
            return d
    return None


def update_draft_status(draft_id: str, new_status: str) -> Optional[Dict[str, Any]]:
    """
    Update the status of a specific draft in-place in the log file.
    Returns the updated draft dict, or None if not found.
    """
    drafts = read_all_drafts()
    updated_entry = None
    for entry in drafts:
        if entry.get("draft_id") == draft_id:
            entry["status"] = new_status
            updated_entry = entry
            break
    if updated_entry is None:
        return None
    # Write back all entries
    DRAFTS_FILE.parent.mkdir(exist_ok=True)
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        for entry in drafts:
            f.write(json.dumps(entry) + "\n")
    return updated_entry