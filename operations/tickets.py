"""A10: total ticket sales (units * price) for a given ticket type."""
from __future__ import annotations

import sqlite3

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_query_tickets(ticket_type: str) -> str:
    ticket_type = ticket_type.capitalize()
    db_path = validate_path("ticket-sales.db", settings.data_dir)
    output_path = validate_path(
        f"ticket-sales-{ticket_type.lower()}.txt", settings.data_dir
    )
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found")

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT SUM(units * price) FROM tickets WHERE type = ?", (ticket_type,))
        result = cur.fetchone()[0]

    output_path.write_text(str(result), encoding="utf-8")
    return (
        f"Operation 'query_tickets' completed: total {ticket_type} ticket "
        f"sales = {result}."
    )
