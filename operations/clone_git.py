"""Clone a git repo into /data/git_repos and make a commit."""
from __future__ import annotations

import os
import subprocess

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_clone_git(repo_url: str, commit_message: str) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1]
    clone_dir = validate_path(os.path.join("git_repos", repo_name), settings.data_dir)
    clone_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "clone", repo_url, str(clone_dir)], check=True, capture_output=True)
        dummy_file = clone_dir / "dummy.txt"
        dummy_file.write_text("This is a dummy commit.", encoding="utf-8")
        subprocess.run(["git", "-C", str(clone_dir), "add", "dummy.txt"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(clone_dir), "commit", "-m", commit_message],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git operation failed: {e}") from e
    return (
        f"Operation 'clone_git' completed: repo cloned and committed with "
        f"message '{commit_message}'."
    )
