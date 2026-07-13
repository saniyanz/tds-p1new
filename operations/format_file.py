"""A1/A2: format format.md using Prettier."""
from __future__ import annotations

import platform
import subprocess

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_format_file() -> str:
    filepath = validate_path("format.md", settings.data_dir)
    if not filepath.exists():
        raise FileNotFoundError(f"{filepath} not found")

    npx_cmd = "npx.cmd" if platform.system() == "Windows" else "npx"
    cmd = [npx_cmd, "prettier@3.4.2", "--write", str(filepath)]
    try:
        subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"prettier failed: {e.stderr}") from e
    return "Operation 'format_file' completed: format.md formatted using prettier@3.4.2."
