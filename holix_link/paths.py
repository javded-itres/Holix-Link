"""Portable workspace jail for Holix Link client."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath


class LinkJailError(PermissionError):
    """Raised when a path escapes the configured workspace root."""


_UNC_PREFIX_RE = re.compile(r"^\\\\[^\\]+\\[^\\]+")


def to_portable_relative(root: Path, absolute: Path) -> str:
    """Map an absolute path under *root* to a portable relative path (POSIX-style)."""
    root_resolved = _resolve_root(root)
    target = _resolve_target(absolute)
    if not _is_under_root(target, root_resolved):
        raise LinkJailError(f"Path '{target}' is outside workspace '{root_resolved}'")
    rel = target.relative_to(root_resolved)
    return rel.as_posix()


def normalize_relative_path(raw: str) -> str:
    """Normalize a user/agent path to a safe portable relative path."""
    cleaned = raw.strip().replace("\\", "/")
    if not cleaned or cleaned in (".", "/"):
        return ""

    pure = PurePosixPath(cleaned)
    if pure.is_absolute():
        raise LinkJailError(f"Absolute paths are not allowed: {raw!r}")

    parts: list[str] = []
    for part in pure.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise LinkJailError(f"Parent segments are not allowed: {raw!r}")
        parts.append(part)

    return "/".join(parts)


def resolve_in_jail(root: Path, raw: str) -> Path:
    """Resolve a portable relative path inside the workspace jail."""
    root_resolved = _resolve_root(root)
    rel = normalize_relative_path(raw)
    candidate = root_resolved if not rel else root_resolved / rel
    resolved = _resolve_target(candidate)

    if not _is_under_root(resolved, root_resolved):
        raise LinkJailError(
            f"Path '{resolved}' escapes workspace jail '{root_resolved}'"
        )
    return resolved


def is_unc_path(raw: str) -> bool:
    return bool(_UNC_PREFIX_RE.match(raw.strip()))


def resolve_folder_root(path: Path) -> Path:
    """Resolve and normalize a user-selected workspace folder."""
    return _resolve_root(path)


def _resolve_root(root: Path) -> Path:
    expanded = root.expanduser()
    if is_unc_path(str(expanded)):
        return Path(os.path.normpath(str(expanded)))
    return expanded.resolve()


def _resolve_target(path: Path) -> Path:
    text = str(path)
    if is_unc_path(text):
        return Path(os.path.normpath(text))
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _is_under_root(target: Path, root: Path) -> bool:
    try:
        return target.is_relative_to(root)
    except AttributeError:
        root_s = str(root)
        target_s = str(target)
        return target_s == root_s or target_s.startswith(root_s + os.sep)