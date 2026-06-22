"""
ADK wrappers for the Spend Guardian agents.
Each agent's existing run() function is passed directly as a tool.
"""
from typing import Any, Dict, List, Union

from google.adk import Agent

from agents import ingestion, classification, waste_detection, recommendation, action


def ingest_transactions(input_data: Union[str, Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Ingest transactions."""
    return ingestion.run(input_data)


def classify_transactions(input_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Classify transactions."""
    return classification.run(input_data)


def detect_waste(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect waste from transactions and matches."""
    return waste_detection.run(input_data)


def generate_recommendations(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate savings reports from waste flags."""
    return recommendation.run(input_data)


def draft_action(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Draft outreach messages from a selected waste flag."""
    return action.run(input_data)


# ADK agents – functions passed directly as tools
ingestion_agent = Agent(
    name="IngestionAgent",
    tools=[ingest_transactions],
    instruction="You are an ingestion agent. Use your tool to ingest transactions.",
)

classification_agent = Agent(
    name="ClassificationAgent",
    tools=[classify_transactions],
    instruction="You are a classification agent. Use your tool to classify transactions.",
)

waste_detection_agent = Agent(
    name="WasteDetectionAgent",
    tools=[detect_waste],
    instruction="You are a waste detection agent. Use your tool to detect waste.",
)

recommendation_agent = Agent(
    name="RecommendationAgent",
    tools=[generate_recommendations],
    instruction="You are a recommendation agent. Use your tool to generate savings reports.",
)

action_agent = Agent(
    name="ActionAgent",
    tools=[draft_action],
    instruction="You are an action agent. Use your tool to draft an outreach message.",
)