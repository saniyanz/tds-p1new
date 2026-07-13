"""Convert a Markdown file to HTML and save it under /data."""
from __future__ import annotations

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

import markdown

logger = get_logger(__name__)


def handle_md_to_html(input_md_filename: str, output_html_filename: str) -> str:
    input_path = validate_path(input_md_filename, settings.data_dir)
    output_path = validate_path(output_html_filename, settings.data_dir)
    md_text = input_path.read_text(encoding="utf-8")
    html = markdown.markdown(md_text)
    output_path.write_text(html, encoding="utf-8")
    return f"Operation 'md_to_html' completed: saved to {output_html_filename}."
