import os
import json
import requests
from datetime import datetime
from typing import Dict, Any

def post_draft_to_slack(flag_id: str, action: str, reasoning: str, potential_savings: float) -> Dict[str, Any]:
    """
    Posts a draft decision to a private Slack channel.
    This is the ONLY "send" capability — it is structurally blocked from sending real emails.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        print("⚠️  SLACK_WEBHOOK_URL not found in .env. Falling back to console mock.")
        return {
            "status": "mock",
            "message": f"[MOCK] Would post: {flag_id} | {action} | ${potential_savings}"
        }

    # Build the Slack message
    message = {
        "text": f"*Spend Guardian Action Required*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Action Approved: {flag_id}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Action:*\n{action}"},
                    {"type": "mrkdwn", "text": f"*Potential Savings:*\n${potential_savings:.2f}/mo"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reasoning:*\n{reasoning}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Approved on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • This is a draft — human must execute the actual cancellation."}
                ]
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        return {
            "status": "sent",
            "channel": "slack",
            "message": f"Successfully posted to Slack for flag {flag_id}"
        }
    except Exception as e:
        # Hard fail: we want to know if Slack breaks
        print(f"❌ FATAL: Failed to post to Slack: {e}")
        raise RuntimeError(f"Slack action agent failed: {e}")