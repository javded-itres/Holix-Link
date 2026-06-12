"""Windows and UNC path normalization tests (platform-mocked)."""

from __future__ import annotations

import sys
from unittest.mock import patch

from holix_link.paths import is_unc_path, normalize_relative_path, resolve_in_jail


def test_is_unc_path() -> None:
    assert is_unc_path(r"\\server\share\folder")
    assert is_unc_path(r"\\server\share")
    assert not is_unc_path(r"C:\Users\me")
    assert not is_unc_path("src/main.py")


def test_normalize_windows_backslashes() -> None:
    assert normalize_relative_path(r"src\lib\util.py") == "src/lib/util.py"


@patch.object(sys, "platform", "win32")
def test_resolve_windows_style_paths(tmp_path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    sub = root / "docs"
    sub.mkdir()
    (sub / "readme.md").write_text("# Hi\n", encoding="utf-8")

    resolved = resolve_in_jail(root, r"docs\readme.md")
    assert resolved.name == "readme.md"
    assert resolved.is_file()