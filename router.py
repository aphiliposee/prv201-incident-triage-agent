"""Deterministic routing rules: which team gets the ticket, and whether a
human must review it first."""

import config


def route_team(category: str) -> str:
    """Map a validated category to its responsible team."""
    return config.TEAM_ROUTING.get(category, "Triage Desk")


def should_escalate(result, valid: bool):
    """Decide whether an incident needs human review before routing.

    Escalates invalid outputs, critical incidents, and
    classifications with confidence below the threshold.

    Returns (escalate, reason).
    """
    if not valid:
        return(True, "invalid model output")
    if result["severity"] == "critical":
        return(True, "critical severity")
    if result["confidence"] < config.CONFIDENCE_THRESHOLD:
        return(True, "confidence below threshold")
    return(False, "")