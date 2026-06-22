"""
Recommendation Agent.
The agent suggests actions for waste flags but must never assert redundancy as
settled fact; it distinguishes confirmed duplicate charges from flags that
require human review, and never invents usage or dormancy evidence.

Converts WasteFlags into SavingsReports using a HIGH‑tier model.
The LLM writes action/reasoning prose; potential_savings is taken directly
from the flag’s monthly_cost (Hard Rule 6).
"""
import json
from typing import Any, Dict, List, Tuple

from litellm import completion
from pydantic import ValidationError

from schemas.models import SavingsReport, WasteFlag
from routing.model_router import TaskTier, resolve_model


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    input_data must contain:
      - "waste_flags": list of dicts (WasteFlag.model_dump())
      - "transactions": list of dicts (not used for computation, passed for context)
    returns {"savings_reports": [...]}
    """
    flags: List[WasteFlag] = [WasteFlag(**f) for f in input_data.get("waste_flags", [])]
    # transactions not used for cost calculation (cost comes from flags) but accepted for future
    transactions: List[Dict[str, Any]] = input_data.get("transactions", [])

    model = resolve_model(TaskTier.HIGH)
    reports: List[SavingsReport] = []

    for flag in flags:
        flag_context = {
            "flag_id": flag.flag_id,
            "vendor_name": flag.vendor_name,
            "overlap_category": flag.overlap_category,
            "confidence_score": flag.confidence_score.value,
            "reason": flag.reason,
            "monthly_cost": flag.monthly_cost,
            "transaction_ids": flag.transaction_ids,
        }

        prompt = (
            "You are a SaaS spend advisor. Based on the waste flag below, suggest "
            "a concrete action (e.g. 'Cancel subscription', 'Downgrade plan', "
            "'Investigate further', 'Contact vendor') and write a concise reasoning. "
            "You must NOT claim that tools are redundant or that an account is "
            "dormant — you have no usage data. "
            "If the overlap_category is 'exact_duplicate', your action can be direct; "
            "otherwise keep your suggestion cautious and recommend human investigation. "
            "Always note that all flags require human review. "
            "Respond ONLY as JSON: {\"action\": \"...\", \"reasoning\": \"...\"}. "
            f"Flag details: {json.dumps(flag_context)}"
        )

        action, reasoning = _call_llm_with_retry_and_validate(model, prompt, flag)

        report = SavingsReport(
            report_id=f"report_{flag.flag_id}",
            flag_id=flag.flag_id,
            action=action,
            reasoning=reasoning,
            potential_savings=flag.monthly_cost,  # Hard Rule 6: from flag, not LLM
        )
        reports.append(report)

    return {"savings_reports": [r.model_dump() for r in reports]}


def _call_llm_with_retry_and_validate(
    model: str, base_prompt: str, flag: WasteFlag, max_retries: int = 1
) -> Tuple[str, str]:
    """
    Call the HIGH‑tier model, retry once on any schema/parse failure,
    then hard‑fail (Hard Rule 7). Returns (action, reasoning).
    """
    prompt = base_prompt
    for attempt in range(max_retries + 1):
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        raw = response["choices"][0]["message"]["content"]

        # Parse JSON
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            if attempt < max_retries:
                prompt = base_prompt + (
                    f"\n\nYour previous response was not valid JSON: {e}. "
                    "Respond ONLY with valid JSON: {\"action\": \"...\", \"reasoning\": \"...\"}."
                )
                continue
            raise RuntimeError(
                f"Recommendation agent: LLM failed to return valid JSON for flag {flag.flag_id} "
                f"after {max_retries + 1} attempts."
            ) from e

        # Validate required keys exist and are non‑empty strings
        action = parsed.get("action", "")
        reasoning = parsed.get("reasoning", "")
        missing = []
        if not isinstance(action, str) or not action.strip():
            missing.append("'action' (non-empty string)")
        if not isinstance(reasoning, str) or not reasoning.strip():
            missing.append("'reasoning' (non-empty string)")

        if missing:
            if attempt < max_retries:
                prompt = base_prompt + (
                    f"\n\nYour last response was missing or had invalid values for: {', '.join(missing)}. "
                    "Respond ONLY with {\"action\": \"...\", \"reasoning\": \"...\"}."
                )
                continue
            raise RuntimeError(
                f"Recommendation agent: LLM response for flag {flag.flag_id} missing required fields "
                f"after {max_retries + 1} attempts: {', '.join(missing)}"
            )

        # Final validation via Pydantic model creation
        try:
            # We only need to validate fields that go into SavingsReport, not potential_savings (we set that later)
            # But we can construct a temporary SavingsReport to trigger any type errors.
            SavingsReport(
                report_id="temp",
                flag_id=flag.flag_id,
                action=action,
                reasoning=reasoning,
                potential_savings=flag.monthly_cost,
            )
        except ValidationError as ve:
            if attempt < max_retries:
                prompt = base_prompt + (
                    f"\n\nValidation error: {ve}. Please fix your response. "
                    "Respond ONLY with valid JSON: {\"action\": \"...\", \"reasoning\": \"...\"}."
                )
                continue
            raise RuntimeError(
                f"Recommendation agent: LLM response for flag {flag.flag_id} failed Pydantic validation "
                f"after {max_retries + 1} attempts."
            ) from ve

        return action, reasoning

    # Unreachable
    raise RuntimeError(f"Recommendation agent: unexpected error for flag {flag.flag_id}")