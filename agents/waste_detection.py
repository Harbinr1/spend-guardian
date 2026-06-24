"""
Waste Detection Agent.
Identifies exact duplicates (HIGH confidence), category overlaps (MEDIUM confidence),
and named-seat ownership risks (MEDIUM confidence). Always requires human review.
Computes monthly_cost from original transaction amounts — never from an LLM.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List
from collections import defaultdict
import re

from litellm import completion

from schemas.models import WasteFlag, Confidence
from routing.model_router import TaskTier, resolve_model


# Simple regex for named-seat detection. Extend only if you find a clear,
# low-false-positive pattern in real bank descriptions.
NAMED_SEAT_PATTERN = re.compile(r"SEAT:", re.IGNORECASE)


def _parse_date(date_val) -> datetime:
    """Parse a date that may be a string or a datetime.date object."""
    from datetime import date as date_type
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, date_type):
        return datetime(date_val.year, date_val.month, date_val.day)
    return datetime.strptime(date_val, "%Y-%m-%d")

def _exact_duplicate_flags(
    vendor_matches: List[Dict[str, Any]],
    transactions: List[Dict[str, Any]]
) -> List[WasteFlag]:
    txn_by_id = {t["transaction_id"]: t for t in transactions}

    groups = defaultdict(list)
    for vm in vendor_matches:
        tid = vm["transaction_id"]
        txn = txn_by_id.get(tid)
        if txn is None:
            continue
        amount = txn["amount"]
        groups[(vm["vendor_name"], amount)].append((tid, txn["date"]))

    flags = []
    for (vendor, amount), items in groups.items():
        if len(items) < 2:
            continue

        # Sort by date
        items_sorted = sorted(items, key=lambda x: _parse_date(x[1]))

        # Cluster into sub‑groups where consecutive dates are ≤ 3 days apart
        clusters = []
        current_cluster = [items_sorted[0]]
        for i in range(1, len(items_sorted)):
            prev_date = _parse_date(items_sorted[i-1][1])
            curr_date = _parse_date(items_sorted[i][1])
            if abs((curr_date - prev_date).days) <= 3:
                current_cluster.append(items_sorted[i])
            else:
                # Store the previous cluster if it has more than 1 item
                if len(current_cluster) > 1:
                    clusters.append(current_cluster)
                current_cluster = [items_sorted[i]]
        # Don't forget the last cluster
        if len(current_cluster) > 1:
            clusters.append(current_cluster)

        # Create a flag for each duplicate cluster
        for cluster in clusters:
            tids = [item[0] for item in cluster]
            monthly_cost = sum(txn_by_id[tid]["amount"] for tid in tids if txn_by_id.get(tid))

            flags.append(WasteFlag(
                flag_id=f"exact_dup_{vendor}_{amount}",
                vendor_name=vendor,
                overlap_category="exact_duplicate",
                confidence_score=Confidence.HIGH,
                requires_human_review=True,
                reason=(
                    f"Exact duplicate charge: {vendor} for {amount} appears "
                    f"{len(tids)} times, with at least two charges within 3 days."
                ),
                transaction_ids=tids,
                monthly_cost=monthly_cost,
            ))
    return flags

def _category_overlap_flags(
    vendor_matches: List[Dict[str, Any]],
    transactions: List[Dict[str, Any]]
) -> List[WasteFlag]:
    """
    For every category that has two or more different vendors, use the MEDIUM
    model to assess the overlap in a single batched prompt.
    Hard-cap confidence at MEDIUM and force requires_human_review=True in code,
    ignoring what the model returns.
    """
    txn_by_id = {t["transaction_id"]: t for t in transactions}

    # Group vendor_matches by category
    cat_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for vm in vendor_matches:
        cat_map[vm["category"]].append(vm)

    # Build a list of all categories that have >=2 vendors
    categories_to_assess = []
    category_data = {}
    for category, items in cat_map.items():
        vendors = set(vm["vendor_name"] for vm in items)
        if len(vendors) >= 2:
            categories_to_assess.append(category)
            category_data[category] = {
                "vendors": sorted(vendors),
                "transaction_ids": [vm["transaction_id"] for vm in items],
                "monthly_cost": sum(
                    txn_by_id[vm["transaction_id"]]["amount"]
                    for vm in items if vm["transaction_id"] in txn_by_id
                ),
            }

    if not categories_to_assess:
        return []

    # Create a single batched prompt for all overlapping categories
    batch_prompt = (
        "You are a spend‑audit assistant. For each category below, write a careful, evidence‑based "
        "reasoning that mentions the category overlap and notes that distinct use cases may exist. "
        "You must NOT claim redundancy. "
        "Respond ONLY as a JSON object where each key is the exact category name and the value is a string with the reasoning.\n\n"
    )
    for cat in categories_to_assess:
        vendor_list = ", ".join(category_data[cat]["vendors"])
        batch_prompt += f'"{cat}": "Multiple vendors in category \'{cat}\': {vendor_list}. ...",\n'
    batch_prompt += "\nYour response must be valid JSON with exactly those keys."

    model = resolve_model(TaskTier.MEDIUM)
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": batch_prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        content = response["choices"][0]["message"]["content"]
        batch_result = json.loads(content)
    except Exception:
        # Fallback: generate simple reasoning for each category
        batch_result = {}
        for cat in categories_to_assess:
            vendor_list = ", ".join(category_data[cat]["vendors"])
            batch_result[cat] = (
                f"Multiple vendors in category '{cat}': {vendor_list}. "
                "No usage data available to confirm distinct use cases."
            )

    # Build flags using the batched results
    flags = []
    for cat in categories_to_assess:
        reasoning = batch_result.get(cat, "")
        if not reasoning:
            vendor_list = ", ".join(category_data[cat]["vendors"])
            reasoning = (
                f"Multiple vendors in category '{cat}': {vendor_list}. "
                "No usage data available to confirm distinct use cases."
            )
        flags.append(WasteFlag(
            flag_id=f"cat_overlap_{cat}",
            vendor_name=", ".join(category_data[cat]["vendors"]),
            overlap_category="category_overlap",
            confidence_score=Confidence.MEDIUM,
            requires_human_review=True,
            reason=reasoning,
            transaction_ids=category_data[cat]["transaction_ids"],
            monthly_cost=category_data[cat]["monthly_cost"],
        ))

    return flags


def _named_seat_flags(transactions: List[Dict[str, Any]]) -> List[WasteFlag]:
    """
    Deterministic flag for transactions whose description suggests
    billing to a named individual (e.g. contains 'SEAT:').
    """
    matched_tids = []
    for txn in transactions:
        if NAMED_SEAT_PATTERN.search(txn.get("raw_description", "")):
            matched_tids.append(txn["transaction_id"])

    if not matched_tids:
        return []

    monthly_cost = sum(txn["amount"] for txn in transactions if txn["transaction_id"] in matched_tids)

    flag = WasteFlag(
        flag_id="named_seat_ownership",
        vendor_name="(multiple)",   # could be multiple vendors
        overlap_category="named_seat_ownership_unclear",
        confidence_score=Confidence.MEDIUM,
        requires_human_review=True,
        reason="Billed to a named individual seat — verify the person is still active.",
        transaction_ids=matched_tids,
        monthly_cost=monthly_cost,
    )
    return [flag]


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts a dict with keys 'transactions' and 'vendor_matches',
    returns {'waste_flags': [...]}.
    """
    transactions = input_data.get("transactions", [])
    vendor_matches = input_data.get("vendor_matches", [])

    flags: List[WasteFlag] = []
    flags.extend(_exact_duplicate_flags(vendor_matches, transactions))
    flags.extend(_category_overlap_flags(vendor_matches, transactions))
    flags.extend(_named_seat_flags(transactions))

    return {"waste_flags": [f.model_dump() for f in flags]}