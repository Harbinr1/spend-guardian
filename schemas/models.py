"""
Pydantic schemas for the Spend Guardian agent pipeline.

Every agent boundary validates against one of these models. This is the
primary defense against silent schema drift, which is the most common
agent-pipeline failure: a model returns JSON that almost matches the
expected shape, and the pipeline doesn't crash — it just produces garbage
that looks plausible.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionStatus(str, Enum):
    DRAFTED = "DRAFTED"
    APPROVED = "APPROVED"
    SENT = "SENT"


class Transaction(BaseModel):
    """Raw transaction parsed from a bank/credit-card statement."""

    transaction_id: str
    date: date
    raw_description: str
    amount: float
    currency: str = "CHF"


class VendorMatch(BaseModel):
    """Output of the Classification agent — one per transaction."""

    transaction_id: str
    vendor_name: str
    category: str
    match_method: str  # "rule_lookup" | "llm_fallback"
    match_confidence: Confidence


class WasteFlag(BaseModel):
    """
    Output of the Waste-Detection agent.

    Never asserts that an overlap IS waste — only surfaces overlap with an
    explicit confidence level and reasoning. Category overlap is capped at
    MEDIUM and always requires human review. Only an exact duplicate
    charge (same vendor, same amount, within 3 days) may reach HIGH — and
    even then, still requires review.
    """

    flag_id: str
    vendor_name: str
    overlap_category: str  # "exact_duplicate" | "category_overlap" | "named_seat_ownership_unclear"
    confidence_score: Confidence
    requires_human_review: bool = True
    reason: str
    transaction_ids: List[str]
    monthly_cost: float


class SavingsReport(BaseModel):
    """Output of the Recommendation agent — one per WasteFlag."""

    report_id: str
    flag_id: str
    action: str
    reasoning: str
    potential_savings: float


class ActionDraft(BaseModel):
    """
    Output of the Action agent. The only object that can ever lead to an
    external action (Gmail/Slack MCP), and it only ever represents a
    draft. Status never advances past DRAFTED inside the agent pipeline
    itself — only an explicit human approval call in the API/CLI can move
    it forward.
    """

    draft_id: str
    flag_id: str
    recipient: str
    subject: str
    body: str
    status: ActionStatus = ActionStatus.DRAFTED


class PipelineState(BaseModel):
    """Shared state object passed through every stage of the orchestrator."""

    transactions: List[Transaction] = Field(default_factory=list)
    vendor_matches: List[VendorMatch] = Field(default_factory=list)
    waste_flags: List[WasteFlag] = Field(default_factory=list)
    savings_reports: List[SavingsReport] = Field(default_factory=list)
    action_drafts: List[ActionDraft] = Field(default_factory=list)