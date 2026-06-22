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
    model to assess the overlap. Hard-cap confidence at MEDIUM and force
    requires_human_review=True in code, ignoring what the model returns.
    """
    txn_by_id = {t["transaction_id"]: t for t in transactions}

    # Group vendor_matches by category
    cat_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for vm in vendor_matches:
        cat_map[vm["category"]].append(vm)

    model = resolve_model(TaskTier.MEDIUM)
    flags = []

    for category, items in cat_map.items():
        # Distinct vendors in this category
        vendors = set(vm["vendor_name"] for vm in items)
        if len(vendors) < 2:
            continue

        vendor_list = ", ".join(sorted(vendors))
        prompt = (
            "You are a spend‑audit assistant. The following vendors are all "
            f"categorised as '{category}': {vendor_list}. "
            "Because you only have bank transaction data and no usage data, "
            "you cannot assert redundancy. Write a careful, evidence‑based "
            "reasoning that mentions the category overlap and notes that "
            "distinct use cases may exist. "
            "Respond ONLY as JSON: {\"reasoning\": \"...\"}"
        )

        try:
            response = completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
                max_tokens=200,
            )
            content = response["choices"][0]["message"]["content"]
            llm_output = json.loads(content)
            reasoning = llm_output.get("reasoning", "")
        except Exception:
            reasoning = (
                f"Multiple vendors in category '{category}': {vendor_list}. "
                "No usage data available to confirm distinct use cases."
            )

        # Collect all transaction_ids for this category
        tids = [vm["transaction_id"] for vm in items]
        monthly_cost = sum(txn_by_id[tid]["amount"] for tid in tids if txn_by_id.get(tid))

        flag = WasteFlag(
            flag_id=f"cat_overlap_{category}",
            vendor_name=", ".join(sorted(vendors)),   # aggregate
            overlap_category="category_overlap",
            confidence_score=Confidence.MEDIUM,       # hard‑capped
            requires_human_review=True,               # forced
            reason=reasoning,
            transaction_ids=tids,
            monthly_cost=monthly_cost,
        )
        flags.append(flag)

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