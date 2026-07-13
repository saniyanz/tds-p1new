"""A4: sort contacts.json by last_name then first_name."""
from __future__ import annotations

import json

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_sort_contacts() -> str:
    input_path = validate_path("contacts.json", settings.data_dir)
    output_path = validate_path("contacts-sorted.json", settings.data_dir)
    with open(input_path, encoding="utf-8") as f:
        contacts = json.load(f)

    sorted_contacts = sorted(
        contacts, key=lambda c: (c.get("last_name", ""), c.get("first_name", ""))
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_contacts, f, indent=2)
    return "Operation 'sort_contacts' completed: contacts sorted."
