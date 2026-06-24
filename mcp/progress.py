import json
import datetime
from pathlib import Path

PROGRESS_FILE = Path("runs/progress.json")

def set_progress(stage: str) -> None:
    """Writes the current progress stage to the file."""
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    data = {
        "stage": stage,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_progress() -> dict:
    """Reads the current progress stage from the file."""
    if not PROGRESS_FILE.exists():
        return {"stage": "idle"}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"stage": "idle"}

def clear_progress() -> None:
    """Deletes the progress file."""
    if PROGRESS_FILE.exists():
        try:
            PROGRESS_FILE.unlink()
        except OSError:
            pass
