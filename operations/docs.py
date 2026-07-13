"""A6: index Markdown docs by their first H1 heading."""
from __future__ import annotations

import json
import os

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_index_docs() -> str:
    docs_dir = validate_path("docs", settings.data_dir)
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"{docs_dir} not found")

    index: dict[str, str] = {}
    for root, _dirs, files in os.walk(docs_dir):
        for file in files:
            if not file.endswith(".md"):
                continue
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, docs_dir)
            title = None
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if line.lstrip().startswith("#"):
                        title = line.lstrip("#").strip()
                        break
            if title:
                index[rel_path] = title

    output_path = validate_path("docs/index.json", settings.data_dir)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    return "Operation 'index_docs' completed: Markdown docs indexed."
