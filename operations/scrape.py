"""Scrape a website and save its extracted text under /data."""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    )
}


def handle_scrape_website(url: str, output_filename: str) -> str:
    output_path = validate_path(output_filename, settings.data_dir)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(separator="\n")
    output_path.write_text(page_text, encoding="utf-8")
    return (
        f"Operation 'scrape_website' completed: data from {url} saved to "
        f"{output_filename}."
    )
