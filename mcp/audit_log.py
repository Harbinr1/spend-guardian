# mcp/audit_log.py
import json
from datetime import datetime
from pathlib import Path

AUDIT_LOG = Path("runs/audit.log")

def log_audit_entry(action: str, details: dict):
    """Append a JSON line to the audit log."""
    AUDIT_LOG.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        **details
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")