"""
Action Agent.
Generates an ActionDraft from a single human‑selected WasteFlag.
The agent has NO send/cancel tools structurally; status is always DRAFTED.
Hard Rule 4: Only external approval (API/CLI) can move status past DRAFTED.
"""
import json
from typing import Any, Dict

from litellm import completion

from schemas.models import ActionDraft, ActionStatus, WasteFlag
from routing.model_router import TaskTier, resolve_model


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    input_data must contain:
      - "waste_flag": dict (WasteFlag.model_dump())
      - "recipient": str (email address for the draft)
    returns {"action_draft": {...}}
    """
    flag_dict = input_data.get("waste_flag")
    if not flag_dict:
        raise ValueError("Action agent requires a single 'waste_flag' in input_data.")
    flag = WasteFlag(**flag_dict)
    recipient = input_data.get("recipient", "finance@example.com")

    model = resolve_model(TaskTier.HIGH)

    # Restatement (AGENTS.md): This agent is only allowed to draft outreach
    # messages in status DRAFTED, and is not allowed to make any external
    # changes, call send/cancel actions directly, or advance status past DRAFTED.

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
        "You are an assistant that drafts concise, professional emails to vendors "
        "or internal finance teams regarding a potential SaaS subscription issue. "
        "You have NO authority to cancel or change anything — you are only drafting. "
        "Write a draft email with a subject line and body. "
        "The body should clearly state the issue (based on the flag), propose an action, "
        "and ask for confirmation. Respond ONLY as JSON: "
        '{"subject": "...", "body": "..."}. '
        f"Flag details: {json.dumps(flag_context)}"
    )

    subject, body = _call_llm_with_retry(model, prompt, flag.flag_id)

    draft = ActionDraft(
        draft_id=f"draft_{flag.flag_id}",
        flag_id=flag.flag_id,
        recipient=recipient,
        subject=subject,
        body=body,
        status=ActionStatus.DRAFTED,  # Hard Rule 4: always DRAFTED
    )

    return {"action_draft": draft.model_dump()}


def _call_llm_with_retry(model: str, base_prompt: str, flag_id: str, max_retries: int = 1):
    """Hard Rule 7: retry once on malformed output, then hard‑fail."""
    prompt = base_prompt
    for attempt in range(max_retries + 1):
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            # No response_format — some Groq models struggle with JSON mode on long free text
            max_tokens=500,
        )
        raw = response["choices"][0]["message"]["content"]
        # Try to extract JSON from the response (handle common markdown code blocks)
        try:
            # Strip possible code fences
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            parsed = json.loads(cleaned)
            subject = parsed["subject"]
            body = parsed["body"]
            if not isinstance(subject, str) or not isinstance(body, str):
                raise ValueError("Subject and body must be strings.")
            if not subject.strip() or not body.strip():
                raise ValueError("Subject and body cannot be empty.")
            return subject, body
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            if attempt < max_retries:
                prompt = base_prompt + (
                    f"\n\nYour previous response was invalid: {e}. "
                    "You must respond with ONLY a valid JSON object with keys 'subject' and 'body'. "
                    "Example: {\"subject\": \"...\", \"body\": \"...\"}"
                )
            else:
                raise RuntimeError(
                    f"Action agent: LLM failed to return valid draft for flag {flag_id} "
                    f"after {max_retries + 1} attempts."
                ) from e
    raise RuntimeError(f"Action agent: unexpected error for flag {flag_id}")