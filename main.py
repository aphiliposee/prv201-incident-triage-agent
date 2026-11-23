"""Run the triage pipeline over the alert dataset.

    python main.py          # real run using the Gemini API (needs GEMINI_API_KEY)
    python main.py --mock   # offline run using the keyword stand-in (no key needed)

Pipeline per alert:  prompt -> classifier -> validator -> routing rules -> mock ticket
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import config
import llm
from router import route_team, should_escalate
from tickets import create_ticket, reset_ticket_store
from validator import validate


def triage_alert(alert: dict, classify) -> dict:
    """Process one alert and return the ticket fields (not yet stored)."""
    raw_output, error = None, None
    try:
        raw_output = classify(alert)
        valid, result, error = validate(raw_output)
    except Exception as exc:  # API/network failure must not stop the whole run
        valid, result, error = False, None, f"classifier error: {exc}"

    escalate, reason = should_escalate(result if valid else None, valid)
    if not valid:
        reason = f"{reason} ({error})" if reason else error

    return {
        "alert_id": alert.get("alert_id"),
        "status": "needs_human_review" if escalate else "routed",
        "severity": result["severity"] if valid else None,
        "category": result["category"] if valid else None,
        "summary": result["summary"] if valid else None,
        "confidence": result["confidence"] if valid else None,
        # Invalid output has no category, so there is no team to suggest.
        "team": route_team(result["category"]) if valid else None,
        "escalation_reason": reason or None,
        "valid_output": valid,
        "raw_model_output": raw_output,  # kept for traceability / debugging
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI incident triage agent")
    parser.add_argument("--mock", action="store_true",
                        help="use the offline keyword classifier instead of Gemini")
    parser.add_argument("--input", type=Path, default=config.DATA_FILE,
                        help="alert dataset (JSON list)")
    parser.add_argument("--delay", type=float, default=None,
                        help="seconds between API calls (default: 4 for Gemini, 0 for mock)")
    args = parser.parse_args()

    mode = "mock" if args.mock else "gemini"
    classify = llm.classify_mock if args.mock else llm.classify_with_gemini
    delay = args.delay if args.delay is not None else (0 if args.mock else 4)
    classifier_name = "keyword-mock" if args.mock else config.GEMINI_MODEL

    try:
        alerts = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not load alerts from {args.input}: {exc}", file=sys.stderr)
        return 1

    if not args.mock:
        try:
            llm._get_client()  # fail fast with a clear message if the key is missing
        except Exception as exc:
            print(exc, file=sys.stderr)
            return 1

    tickets_path = config.OUTPUT_DIR / f"tickets_{mode}.json"
    reset_ticket_store(tickets_path)
    run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"Triage run ({classifier_name}) on {len(alerts)} alerts -> {tickets_path}\n")

    for i, alert in enumerate(alerts):
        if i and delay:
            time.sleep(delay)  # stay under free-tier rate limits
        fields = triage_alert(alert, classify)
        ticket = create_ticket(tickets_path, {
            **fields,
            "classifier": classifier_name,
            "run_started": run_started,
        })
        flag = "HUMAN REVIEW" if ticket["status"] == "needs_human_review" else "routed"
        print(f"{ticket['ticket_id']}  {ticket['alert_id']}  "
              f"{str(ticket['severity']):<8} {str(ticket['category']):<14} "
              f"-> {str(ticket['team']):<20} [{flag}]"
              + (f"  reason: {ticket['escalation_reason']}" if ticket["escalation_reason"] else ""))

    print(f"\nDone. Evaluate with: python evaluate.py{' --mock' if args.mock else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
