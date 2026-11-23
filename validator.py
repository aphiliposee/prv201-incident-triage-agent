"""Schema check for model output.

The LLM's response is treated as untrusted. Only output that passes every check
here may be routed automatically. Anything else goes to human review.
"""

import json
import config

REQUIRED_FIELDS = ["severity", "category", "summary", "confidence"]


def validate(raw_text: str):
    """Parse and check a raw model response.

    Returns (is_valid, data, error):
      - (True, cleaned_dict, None) when the output is usable
      - (False, None, "reason") otherwise. This function never raises.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return False, None, "empty response"

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return False, None, f"not valid JSON: {exc.msg}"

    if not isinstance(data, dict):
        return False, None, "response is not a JSON object"

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return False, None, f"missing fields: {', '.join(missing)}"

    severity = str(data["severity"]).strip().lower()
    if severity not in config.SEVERITIES:
        return False, None, f"invalid severity: {data['severity']!r}"

    category = str(data["category"]).strip().lower()
    if category not in config.CATEGORIES:
        return False, None, f"invalid category: {data['category']!r}"

    summary = data["summary"]
    if not isinstance(summary, str) or not summary.strip():
        return False, None, "summary must be a non-empty string"
    if len(summary) > config.MAX_SUMMARY_LENGTH:
        return False, None, f"summary longer than {config.MAX_SUMMARY_LENGTH} characters"

    confidence = data["confidence"]
    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return False, None, "confidence must be a number"
    if not 0.0 <= confidence <= 1.0:
        return False, None, "confidence must be between 0 and 1"

    cleaned = {
        "severity": severity,
        "category": category,
        "summary": summary.strip(),
        "confidence": float(confidence),
    }
    return True, cleaned, None
