"""
Ingestion Agent.
Deterministic CSV/row parsing and credit-card redaction. No LLM calls.
"""
import csv
import io
import re
from typing import Any, Dict, List, Union
from mcp.audit_log import log_audit_entry
from schemas.models import Transaction

# Matches 13-19 digit sequences (credit-card shapes), allowing spaces/dashes between digits
CC_REGEX = re.compile(r"\b(?:\d[ -]*){13,19}\b")


def redact_card_numbers(text: str) -> str:
    """Redacts card-number-shaped digit sequences from free text."""
    return CC_REGEX.sub("XXXX-XXXX-XXXX-XXXX", text or "")


def _rows_from_csv_string(csv_text: str) -> List[Dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Accepts either CSV-style ('description') or fixture-style
    ('raw_description') column names and returns one normalized shape."""
    return {
        "date": row.get("date", ""),
        "raw_description": row.get("raw_description", row.get("description", "")),
        "amount": row.get("amount", "0"),
        "currency": row.get("currency", "CHF") or "CHF",
    }


def run(raw_data: Union[str, Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Accepts: a raw CSV string, a dict with a "csv_data" key, or a list of
    row dicts (e.g. from a JSON sandbox fixture). Returns
    {"transactions": [...]} as plain dicts.
    """
    if isinstance(raw_data, list):
        rows = raw_data
    elif isinstance(raw_data, dict):
        csv_text = raw_data.get("csv_data", "") or raw_data.get("raw_data", "")
        rows = _rows_from_csv_string(csv_text)
    else:
        rows = _rows_from_csv_string(str(raw_data))

    transactions: List[Transaction] = []
    warnings: List[str] = []

    for i, raw_row in enumerate(rows):
        row = _normalize_row(raw_row)
        try:
            clean_description = redact_card_numbers(row["raw_description"])
            txn = Transaction(
                transaction_id=f"txn_{i}",
                date=row["date"],
                raw_description=clean_description,
                amount=float(row["amount"]),
                currency=row["currency"],
            )
            transactions.append(txn)
        except Exception as exc:
            # Per agents/ingestion.md: "Malformed rows are logged and skipped"
            log_audit_entry("ingestion_error", {"row": row, "error": str(exc)})
            warnings.append(f"Skipped malformed row {i + 1}: {exc}")
            continue

    return {"transactions": [t.model_dump() for t in transactions], "warnings": warnings}


if __name__ == "__main__":
    sample_csv = (
        "date,description,amount,currency\n"
        '2026-06-01,"SLACK TECH * MONTHLY 4111111111111111",150.00,CHF\n'
        '2026-06-02,"ADOBE CREATIVE CLOUD",54.99,CHF\n'
        '2026-06-03,"AWS WEB SERVICES 5500000000000004",312.40,USD\n'
    )
    print(run(sample_csv))