"""Shared constants for the incident triage agent.

Everything the rest of the code treats as "policy" (allowed labels, routing
table, escalation threshold, model name) lives here so it can be changed in
one place.
"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR / "data" / "alerts.json"
OUTPUT_DIR = PROJECT_DIR / "output"

# Severity classification policy. This is the single source of truth: the
# Gemini prompt is built from it, and the dataset labels follow it.
SEVERITY_POLICY = {
    "low": "Minor or no immediate impact.",
    "medium": "Limited disruption or degraded service.",
    "high": "Significant disruption or serious security threat.",
    "critical": "Major outage, active compromise, or imminent data-loss risk.",
}

# Allowed labels the LLM must choose from (enforced by the validator).
SEVERITIES = list(SEVERITY_POLICY)
CATEGORIES = ["network", "database", "security", "application", "infrastructure"]

# Deterministic routing: category -> responsible team.
TEAM_ROUTING = {
    "network": "Network Operations",
    "database": "Database Team",
    "security": "Security Team",
    "application": "Application Support",
    "infrastructure": "Infrastructure Team",
}

# Below this model confidence an incident counts as "uncertain".
CONFIDENCE_THRESHOLD = 0.7

# Maximum summary length accepted from the model (characters).
MAX_SUMMARY_LENGTH = 300


def load_dotenv(path: Path = PROJECT_DIR / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines) so no extra dependency is needed.

    Existing environment variables are never overwritten.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
