# utils/security.py
import re

def redact_card_numbers(text: str) -> str:
    """Replace any 16‑digit card number (with or without hyphens/spaces) with 'XXXX-XXXX-XXXX-XXXX'."""
    # Pattern for 16 digits, optionally separated by spaces or hyphens
    pattern = r'\b(?:\d[ -]*?){13,16}\b'
    return re.sub(pattern, 'XXXX-XXXX-XXXX-XXXX', text)

def redact_transaction_description(raw: str) -> str:
    """Apply redaction to a raw description."""
    return redact_card_numbers(raw)