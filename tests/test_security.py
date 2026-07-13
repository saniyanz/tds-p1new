"""Security tests for path validation."""
from __future__ import annotations

from pathlib import Path

import pytest
from core.security import PathSecurityError, validate_path


def test_inside_allowed(tmp_path: Path):
    p = validate_path("sub/file.txt", tmp_path)
    assert tmp_path in p.parents or p == tmp_path


def test_traversal_rejected(tmp_path: Path):
    with pytest.raises(PathSecurityError):
        validate_path("../../etc/passwd", tmp_path)


def test_absolute_outside_rejected(tmp_path: Path):
    with pytest.raises(PathSecurityError):
        validate_path("/etc/passwd", tmp_path)


def test_symlink_escape_rejected(tmp_path: Path):
    import sys

    if sys.platform == "win32":
        pytest.skip("symlink creation requires elevated privileges on Windows")
    inside = tmp_path / "inside"
    inside.mkdir()
    outside = tmp_path.parent / "outside_secret"
    outside.mkdir(exist_ok=True)
    link = inside / "escape"
    link.symlink_to(outside)
    with pytest.raises(PathSecurityError):
        validate_path("inside/escape/secret.txt", tmp_path)
