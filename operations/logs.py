"""A5: extract the first line of the 10 most recently modified .log files."""
from __future__ import annotations

import glob

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_extract_logs() -> str:
    logs_dir = validate_path("logs", settings.data_dir)
    output_path = validate_path("logs-recent.txt", settings.data_dir)
    if not logs_dir.is_dir():
        raise FileNotFoundError(f"{logs_dir} not found")

    log_files = glob.glob(str(logs_dir / "*.log"))
    log_files.sort(key=lambda x: __import__("os").path.getmtime(x), reverse=True)
    recent_logs = log_files[:10]

    lines = []
    for log in recent_logs:
        with open(log, encoding="utf-8") as f:
            lines.append(f.readline().strip())

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "Operation 'extract_logs' completed: processed recent log files."
