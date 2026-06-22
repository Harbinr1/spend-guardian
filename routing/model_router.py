"""
Tiered model routing for the agent pipeline.

Goal: never spend a large/expensive model call on a task a cheap one (or no
model at all) can do reliably. Routing is keyed off a task-complexity tag
defined in each agent's .md file, not the agent's identity — multiple agents
can legitimately share a tier.

NOTE: exact Groq model IDs change over time. Confirm current available
models in the Groq console/docs before wiring these in, then set them as
environment variables rather than hardcoding — a model deprecation should
require an env var change, not a code change.
"""
from dotenv import load_dotenv
load_dotenv()
import os
from enum import Enum
import litellm
litellm.suppress_debug_info = True


class TaskTier(str, Enum):
    DETERMINISTIC = "deterministic"  # no LLM call at all — pure code/rules
    LOW = "low"                      # cheap/fast model — simple lookups, fallback classification
    MEDIUM = "medium"                # reasoning tasks — waste detection, confidence scoring
    HIGH = "high"                    # synthesis/writing — report summary, email drafts


_TIER_MODEL_ENV = {
    TaskTier.LOW: "MODEL_LOW",
    TaskTier.MEDIUM: "MODEL_MEDIUM",
    TaskTier.HIGH: "MODEL_HIGH",
}


def resolve_model(tier: TaskTier) -> str | None:
    """Returns the LiteLLM model string for a given tier, or None for deterministic tasks."""
    if tier == TaskTier.DETERMINISTIC:
        return None
    env_key = _TIER_MODEL_ENV[tier]
    model = os.environ.get(env_key)
    if not model:
        raise RuntimeError(
            f"No model configured for tier {tier}. Set {env_key} in your "
            f"environment. Confirm current Groq model IDs in Groq's docs "
            f"before choosing values — don't hardcode a guess here."
        )
    return model


# Suggested tier assignment per agent task. Re-tune after you have real
# latency/cost numbers from a few pipeline runs — these are starting points,
# not settled.
AGENT_TIER = {
    "ingestion": TaskTier.DETERMINISTIC,
    "classification_rule_hit": TaskTier.DETERMINISTIC,
    "classification_fallback": TaskTier.LOW,
    "waste_detection": TaskTier.MEDIUM,
    "recommendation": TaskTier.HIGH,
    "action_draft": TaskTier.HIGH,
}