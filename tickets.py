"""Mock ticketing tool: records tickets in a JSON file."""

import json
from pathlib import Path


def reset_ticket_store(path: Path) -> None:
    """Start a fresh ticket file for a new pipeline run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")


def create_ticket(path: Path, ticket: dict) -> dict:
    """Append one ticket to the JSON store and return it with its assigned id."""
    tickets = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    ticket = {"ticket_id": f"TCK-{len(tickets) + 1:04d}", **ticket}
    tickets.append(ticket)
    path.write_text(json.dumps(tickets, indent=2, ensure_ascii=False), encoding="utf-8")
    return ticket
