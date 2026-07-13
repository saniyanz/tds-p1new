"""A3: count dates that fall on a given weekday in dates.txt."""
from __future__ import annotations

import calendar

from core.config import settings
from core.logging import get_logger
from core.security import validate_path
from dateutil.parser import parse

logger = get_logger(__name__)

VALID_DAYS = list(calendar.day_name)


def handle_count_dates(day_name: str) -> str:
    day_name = day_name.capitalize()
    if day_name not in VALID_DAYS:
        raise ValueError(
            f"Invalid day name: {day_name}. Expected one of {VALID_DAYS}."
        )
    target_weekday = VALID_DAYS.index(day_name)

    input_file = validate_path("dates.txt", settings.data_dir)
    output_file = validate_path(f"dates-{day_name.lower()}.txt", settings.data_dir)
    if not input_file.exists():
        raise FileNotFoundError(f"{input_file} not found")

    count = 0
    with open(input_file, encoding="utf-8") as f:
        for line in f:
            date_str = line.strip()
            if not date_str:
                continue
            try:
                dt = parse(date_str, fuzzy=True)
            except Exception:
                logger.debug("skipping invalid date", extra={"date": date_str})
                continue
            if dt.weekday() == target_weekday:
                count += 1

    output_file.write_text(str(count), encoding="utf-8")
    return f"Operation 'count_dates' completed: found {count} {day_name}s."
