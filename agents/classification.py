"""
Classification Agent.
Maps each Transaction to a VendorMatch using a two-tier resolution:
1. Rule-based dictionary lookup (deterministic).
2. LOW-tier LLM fallback for vendor names not in the dictionary.
"""
import json
import re
from typing import Any, Dict, List, Union

from litellm import completion

from schemas.models import Confidence, VendorMatch
from routing.model_router import TaskTier, resolve_model

VENDOR_DICTIONARY = {
    "FIGMA": ("Figma", "Design"),
    "ADOBE": ("Adobe Creative Cloud", "Design"),
    "JIRA": ("Jira", "Project Management"),
    "ASANA": ("Asana", "Project Management"),
    "AWS": ("AWS", "Cloud Infrastructure"),
    "NOTION": ("Notion", "Productivity"),
    "SLACK": ("Slack", "Communication"),
    "ZENDESK": ("Zendesk", "Customer Support"),
}


def _normalize(description: str) -> str:
    text = description.upper()
    text = re.sub(r"[*_/]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _rule_lookup(description: str):
    normalized = _normalize(description)
    for key, value in VENDOR_DICTIONARY.items():
        if key in normalized:
            return value
    return None


def _call_llm(description: str) -> Dict[str, str]:
    model = resolve_model(TaskTier.LOW)
    prompt = (
        "Identify the vendor name and a short category (1-2 words) for this "
        f'transaction description: "{description}". '
        'Respond ONLY as JSON: {"vendor_name": "...", "category": "..."}'
    )
    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    content = response["choices"][0]["message"]["content"]
    parsed = json.loads(content)  # let this raise on the first attempt
    return {"vendor_name": parsed["vendor_name"], "category": parsed["category"]}


def _llm_fallback(description: str) -> Dict[str, str]:
    """One retry on parse failure. Hard-fail on the second attempt —
    never silently return 'Unclassified'."""
    try:
        return _call_llm(description)
    except Exception:
        try:
            return _call_llm(description)
        except Exception as exc:
            raise RuntimeError(
                f"Classification LLM fallback failed twice for description "
                f"'{description}': {exc}"
            )


def _extract_transactions(input_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if isinstance(input_data, dict):
        return input_data.get("transactions", [])
    return input_data


def run(input_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
    transactions = _extract_transactions(input_data)
    vendor_matches: List[VendorMatch] = []

    for i, txn in enumerate(transactions):
        description = txn.get("raw_description", "")
        transaction_id = txn.get("transaction_id", f"txn_{i}")

        rule_result = _rule_lookup(description)
        if rule_result is not None:
            vendor_name, category = rule_result
            match = VendorMatch(
                transaction_id=transaction_id,
                vendor_name=vendor_name,
                category=category,
                match_confidence=Confidence.HIGH,   # was: confidence=
                match_method="rule_lookup",
            )
        else:
            fallback = _llm_fallback(description)
            match = VendorMatch(
                transaction_id=transaction_id,
                vendor_name=fallback["vendor_name"],
                category=fallback["category"],
                match_confidence=Confidence.LOW,    # was: confidence=
                match_method="llm_fallback",
            )
        vendor_matches.append(match)

    return {"vendor_matches": [m.model_dump() for m in vendor_matches]}


if __name__ == "__main__":
    sample = [
        {"transaction_id": "txn_0", "raw_description": "FIGMA INC", "amount": 45.0},
        {"transaction_id": "txn_1", "raw_description": "AWS*EC2-USAGE", "amount": 88.1},
    ]
    print(run(sample))