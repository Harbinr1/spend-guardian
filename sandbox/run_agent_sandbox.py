"""
Run a single agent in isolation against a fixture input, without the rest of
the pipeline. Use this while building each agent — don't wait until the full
orchestrator is wired to discover an individual agent is broken.

Each module in agents/ must expose a `run(fixture_data: dict) -> dict`
function for this to work against it.

Usage:
    python sandbox/run_agent_sandbox.py classification --fixture data/sample_transactions.json
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import argparse
import importlib
import json
from pathlib import Path

AGENT_MODULES = {
    "ingestion": "agents.ingestion",
    "classification": "agents.classification",
    "waste_detection": "agents.waste_detection",
    "recommendation": "agents.recommendation",
    "action": "agents.action",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", choices=AGENT_MODULES.keys())
    parser.add_argument("--fixture", required=True, type=Path)
    args = parser.parse_args()

    module = importlib.import_module(AGENT_MODULES[args.agent])
    fixture_data = json.loads(args.fixture.read_text())

    result = module.run(fixture_data)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()