"""A7: extract the sender email address from email.txt.

NOTE: this is a heuristic regex extraction. For higher accuracy the planner
could route this to an LLM call; kept as a fast deterministic extractor for now.
"""
from __future__ import annotations

import re

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+")


def handle_extract_email() -> str:
    input_path = validate_path("email.txt", settings.data_dir)
    output_path = validate_path("email-sender.txt", settings.data_dir)
    content = input_path.read_text(encoding="utf-8")
    match = EMAIL_RE.search(content)
    sender_email = match.group(0) if match else ""
    output_path.write_text(sender_email, encoding="utf-8")
    return f"Operation 'extract_email' completed: extracted sender email {sender_email}."
