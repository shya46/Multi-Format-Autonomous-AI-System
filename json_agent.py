"""
json_agent.py
-------------
JSON Agent for the Multi-Format Autonomous AI System

Responsibilities
* Parse incoming JSON (string or bytes)
* Validate required fields / types
* Detect anomalies (missing fields, type errors, custom rules)
* Persist full trace to shared SQLite memory (via insert_agent_trace)
* Trigger follow-up action (simulated POST /risk_alert) when anomalies exist
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

# ────────────────────────────────────────────────────────────────────────────
# Local helpers
# ────────────────────────────────────────────────────────────────────────────
from memory import insert_agent_trace, init_db

# Ensure DB/table exists even if this module is invoked standalone
init_db()

# ────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────
REQUIRED_FIELDS: List[Tuple[str, type]] = [
    ("id", int),
    ("timestamp", str),
    ("status", str),
]

RISK_ALERT_ENDPOINT = "http://localhost:8000/risk_alert"  # Simulated API
REQUEST_TIMEOUT     = 4   # seconds
MAX_RETRIES         = 3   # retry logic for HTTP errors

# ────────────────────────────────────────────────────────────────────────────
# Core processing
# ────────────────────────────────────────────────────────────────────────────
def parse_json(raw: str | bytes) -> Dict[str, Any]:
    """Safely parse JSON text/bytes → dict, raising ValueError on failure."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def validate(data: Dict[str, Any]) -> List[str]:
    """Return a list of anomaly strings (empty ⇒ valid)."""
    anomalies: List[str] = []

    # Presence + type checks
    for field, expected_type in REQUIRED_FIELDS:
        if field not in data:
            anomalies.append(f"Missing field: '{field}'")
            continue
        if not isinstance(data[field], expected_type):
            anomalies.append(
                f"Type mismatch for '{field}': expected {expected_type.__name__}, "
                f"got {type(data[field]).__name__}"
            )

    # Custom rule: allowed status values
    allowed_status = {"OPEN", "CLOSED", "IN_PROGRESS"}
    if "status" in data and data["status"] not in allowed_status:
        anomalies.append(
            f"Invalid status '{data['status']}' (allowed: {', '.join(allowed_status)})"
        )

    return anomalies


# ────────────────────────────────────────────────────────────────────────────
# Retry helper
# ────────────────────────────────────────────────────────────────────────────
def post_with_retries(url: str, payload: Dict[str, Any]) -> tuple[bool, str]:
    """POST with retry/backoff. Returns (success, final_error_msg)."""
    backoff = 1
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return True, ""
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                return False, str(exc)
            time.sleep(backoff)
            backoff *= 2


# ────────────────────────────────────────────────────────────────────────────
# Public entry point
# ────────────────────────────────────────────────────────────────────────────
def process_json(
    raw_json: str | bytes,
    *,
    source: str = "webhook",   # use filename if available
    intent: str = "Unknown",
) -> Dict[str, Any]:
    """
    Full agent pipeline:
      1. Parse
      2. Validate / anomaly detection
      3. Trigger follow-up action if needed
      4. Persist to shared memory
      5. Return structured result
    """
    # 1) Parse
    try:
        data = parse_json(raw_json)
    except ValueError as exc:
        agent_result = {"valid": False, "anomalies": [str(exc)], "data": None}
        insert_agent_trace(
            filename     = source,
            file_type    = "JSON",
            intent       = intent,
            agent_result = agent_result,
            action_taken = "parse_error"
        )
        return agent_result

    # 2) Validate
    anomalies = validate(data)
    valid     = len(anomalies) == 0

    # 3) Decide + act
    if valid:
        action_taken = "logged"
    else:
        success, err = post_with_retries(
            RISK_ALERT_ENDPOINT,
            {"data": data, "anomalies": anomalies}
        )
        action_taken = "risk_alert_success" if success else f"risk_alert_failed: {err}"

    # 4) Persist trace
    agent_result = {"valid": valid, "anomalies": anomalies, "data": data}
    insert_agent_trace(
        filename     = source,
        file_type    = "JSON",
        intent       = intent,
        agent_result = agent_result,
        action_taken = action_taken
    )

    # 5) Return
    return agent_result


# ────────────────────────────────────────────────────────────────────────────
# CLI quick-test
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":  # python json_agent.py sample.json
    import sys

    if len(sys.argv) != 2:
        print("Usage: python json_agent.py <json_file>")
        sys.exit(1)

    fp   = Path(sys.argv[1])
    raw  = fp.read_bytes()
    out  = process_json(raw, source=str(fp), intent="WebhookData")
    print(json.dumps(out, indent=2))
