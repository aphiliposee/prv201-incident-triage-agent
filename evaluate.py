"""Compare pipeline tickets to the labelled dataset.

    python evaluate.py          # evaluates output/tickets_gemini.json
    python evaluate.py --mock   # evaluates output/tickets_mock.json
"""

import argparse
import json
import sys

import config

METRICS = ["severity", "category", "team", "escalate"]


def evaluate(alerts: list, tickets: list) -> dict:
    by_id = {t["alert_id"]: t for t in tickets}
    correct = {m: 0 for m in METRICS}
    mismatches = []
    valid_count = 0

    for alert in alerts:
        expected = alert["expected"]
        ticket = by_id.get(alert["alert_id"])
        if ticket is None:
            mismatches.append({"alert_id": alert["alert_id"], "problem": "no ticket created"})
            continue
        valid_count += ticket["valid_output"]
        predicted = {
            "severity": ticket["severity"],
            "category": ticket["category"],
            "team": ticket["team"],
            "escalate": ticket["status"] == "needs_human_review",
        }
        diffs = {}
        for m in METRICS:
            if predicted[m] == expected[m]:
                correct[m] += 1
            else:
                diffs[m] = {"expected": expected[m], "predicted": predicted[m]}
        if diffs:
            mismatches.append({"alert_id": alert["alert_id"], "differences": diffs,
                               # alerts with a label_note have a contested label
                               "ambiguous_label": "label_note" in alert})

    n = len(alerts)
    return {
        "total_alerts": n,
        "valid_output_rate": round(valid_count / n, 3) if n else 0,
        "accuracy": {m: round(correct[m] / n, 3) if n else 0 for m in METRICS},
        "fully_correct": n - len(mismatches),
        "mismatches": mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate triage tickets against labels")
    parser.add_argument("--mock", action="store_true", help="evaluate the mock run's tickets")
    args = parser.parse_args()
    mode = "mock" if args.mock else "gemini"

    tickets_path = config.OUTPUT_DIR / f"tickets_{mode}.json"
    if not tickets_path.exists():
        print(f"{tickets_path} not found. Run: python main.py{' --mock' if args.mock else ''}",
              file=sys.stderr)
        return 1

    alerts = json.loads(config.DATA_FILE.read_text(encoding="utf-8"))
    tickets = json.loads(tickets_path.read_text(encoding="utf-8"))
    report = evaluate(alerts, tickets)
    report["classifier"] = tickets[0]["classifier"] if tickets else mode

    print(f"Evaluation: {report['classifier']}  ({report['total_alerts']} alerts)")
    print(f"  valid structured output : {report['valid_output_rate']:.0%}")
    for m, acc in report["accuracy"].items():
        print(f"  {m + ' accuracy':<24}: {acc:.0%}")
    print(f"  fully correct alerts    : {report['fully_correct']}/{report['total_alerts']}")
    if report["mismatches"]:
        print("\nMismatches:")
        for mm in report["mismatches"]:
            detail = mm.get("problem") or ", ".join(
                f"{k}: expected {v['expected']}, got {v['predicted']}"
                for k, v in mm["differences"].items())
            tag = "  [ambiguous label, see label_note]" if mm.get("ambiguous_label") else ""
            print(f"  {mm['alert_id']}: {detail}{tag}")

    report_path = config.OUTPUT_DIR / f"eval_{mode}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
