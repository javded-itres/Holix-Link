"""Unix-style path jail tests."""

from __future__ import annotations

import pytest

from holix_link.paths import (
    LinkJailError,
    normalize_relative_path,
    resolve_in_jail,
    to_portable_relative,
)


@pytest.fixture
def jail_root(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    return root


def test_normalize_relative_empty() -> None:
    assert normalize_relative_path("") == ""
    assert normalize_relative_path(".") == ""


def test_normalize_relative_posix() -> None:
    assert normalize_relative_path("src/main.py") == "src/main.py"
    assert normalize_relative_path("./src/main.py") == "src/main.py"


def test_normalize_rejects_parent() -> None:
    with pytest.raises(LinkJailError):
        normalize_relative_path("../etc/passwd")


def test_normalize_rejects_absolute() -> None:
    with pytest.raises(LinkJailError):
        normalize_relative_path("/etc/passwd")


def test_resolve_in_jail(jail_root) -> None:
    resolved = resolve_in_jail(jail_root, "src/main.py")
    assert resolved.name == "main.py"
    assert resolved.is_file()


def test_resolve_root_path(jail_root) -> None:
    resolved = resolve_in_jail(jail_root, "")
    assert resolved == jail_root.resolve()


def test_to_portable_relative(jail_root) -> None:
    file_path = jail_root / "src" / "main.py"
    assert to_portable_relative(jail_root, file_path) == "src/main.py"


def test_symlink_escape_blocked(jail_root, tmp_path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    link = jail_root / "escape.txt"
    link.symlink_to(outside)
    with pytest.raises(LinkJailError):
        resolve_in_jail(jail_root, "escape.txt")