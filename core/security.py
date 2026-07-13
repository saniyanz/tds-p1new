"""Path security utilities.

All file access from operations must go through :func:`validate_path` so that
symlink escapes and path traversal outside the data directory are rejected.
"""
from __future__ import annotations

import os
from pathlib import Path


class PathSecurityError(PermissionError):
    """Raised when a path resolves outside the allowed base directory."""


def validate_path(
    path: str | os.PathLike,
    base_dir: str | os.PathLike,
) -> Path:
    """Resolve *path* (relative to *base_dir* if not absolute) and ensure it
    stays within *base_dir*.

    Uses ``Path.resolve()`` so symlinks are expanded before the containment
    check, preventing ``../`` and symlink-based escapes.
    """
    base = Path(base_dir).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()

    if resolved == base or base in resolved.parents:
        return resolved
    raise PathSecurityError(
        f"Access to {resolved} is not allowed (outside {base})."
    )
