"""Fetch JSON/data from an API and save it under /data."""
from __future__ import annotations

import requests
from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_fetch_api(api_url: str, output_filename: str) -> str:
    output_path = validate_path(output_filename, settings.data_dir)
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    output_path.write_text(resp.text, encoding="utf-8")
    return (
        f"Operation 'fetch_api' completed: data fetched from {api_url} and "
        f"saved to {output_filename}."
    )
