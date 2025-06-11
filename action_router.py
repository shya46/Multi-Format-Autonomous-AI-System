# action_router.py
# Dynamically triggers follow-up actions based on agent results

import requests
from typing import Dict, Any
from memory import insert_agent_trace


def route_action(intent: str, agent_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide and trigger follow-up action based on business intent and result.
    Returns a log of the action taken.
    """
    action_log = {
        "action": None,
        "status": "skipped",
        "details": "No action required"
    }

    try:
        if intent == "Complaint":
            tone = agent_result.get("tone")
            urgency = agent_result.get("urgency")

            if tone == "angry" and urgency == "high":
                response = requests.post("http://localhost:8000/crm/escalate", json=agent_result)
                action_log = {
                    "action": "escalate_to_crm",
                    "status": response.status_code,
                    "details": response.json()
                }

        elif intent == "Invoice" and agent_result.get("risk_flag"):
            response = requests.post("http://localhost:8000/risk_alert", json=agent_result)
            action_log = {
                "action": "flag_high_risk_invoice",
                "status": response.status_code,
                "details": response.json()
            }

        elif intent == "Regulation" and agent_result.get("flagged_terms"):
            response = requests.post("http://localhost:8000/compliance_alert", json=agent_result)
            action_log = {
                "action": "compliance_alert",
                "status": response.status_code,
                "details": response.json()
            }

    except Exception as e:
        action_log = {
            "action": "error",
            "status": "failed",
            "details": str(e)
        }

    # Optional: persist the action decision
    insert_agent_trace(
        filename="[action_router]",
        file_type="system",
        intent=intent,
        agent_result=action_log,
        action_taken=action_log["action"] or "none"
    )

    return action_log
