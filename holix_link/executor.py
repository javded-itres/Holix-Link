"""Filesystem RPC executor inside the workspace jail."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from holix_link.config import ClientNotifications
from holix_link.paths import (
    LinkJailError,
    normalize_relative_path,
    resolve_in_jail,
    to_portable_relative,
)
from holix_link.protocol import (
    DirEntry,
    FileStat,
    LinkPermissions,
    RpcCall,
    RpcOp,
    RpcResult,
    RpcResultPayload,
)

logger = logging.getLogger(__name__)

MAX_READ_BYTES = 10 * 1024 * 1024
MAX_WRITE_BYTES = 10 * 1024 * 1024


class PermissionDeniedError(PermissionError):
    """Raised when the link profile disallows an operation."""


class JailExecutor:
    def __init__(
        self,
        root: Path,
        permissions: LinkPermissions,
        notifications: ClientNotifications | None = None,
    ) -> None:
        self._root = root
        self._permissions = permissions
        self._notifications = notifications or ClientNotifications()

    async def execute(self, call: RpcCall) -> RpcResult:
        try:
            payload = self._dispatch(call)
            self._notify(call)
            return RpcResult(id=call.id, ok=True, payload=payload)
        except (
            LinkJailError,
            PermissionDeniedError,
            FileNotFoundError,
            IsADirectoryError,
            ValueError,
        ) as exc:
            return RpcResult(id=call.id, ok=False, error=str(exc))
        except OSError as exc:
            return RpcResult(id=call.id, ok=False, error=f"Filesystem error: {exc}")

    def _dispatch(self, call: RpcCall) -> RpcResultPayload:
        op = call.op
        if op == RpcOp.LIST_DIR:
            self._require(self._permissions.read)
            return RpcResultPayload(entries=self._list_dir(call.path, call.limit or 200))
        if op == RpcOp.READ_FILE:
            self._require(self._permissions.read)
            return RpcResultPayload(**self._read_file(call.path))
        if op == RpcOp.WRITE_FILE:
            self._require(self._permissions.write)
            return RpcResultPayload(bytes_written=self._write_file(call))
        if op == RpcOp.STAT:
            self._require(self._permissions.read)
            return RpcResultPayload(stat=self._stat(call.path))
        if op == RpcOp.MKDIR:
            self._require(self._permissions.mkdir)
            return RpcResultPayload(stat=self._mkdir(call.path))
        if op == RpcOp.DELETE:
            self._require(self._permissions.delete)
            self._delete(call.path)
            return RpcResultPayload()
        raise ValueError(f"Unsupported operation: {op}")

    def _require(self, allowed: bool) -> None:
        if not allowed:
            raise PermissionDeniedError("Operation not permitted for this link")

    def _list_dir(self, raw_path: str, limit: int) -> list[DirEntry]:
        target = resolve_in_jail(self._root, raw_path)
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {raw_path}")

        entries: list[DirEntry] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if child.name.startswith("."):
                continue
            portable = to_portable_relative(self._root, child)
            stat = child.stat()
            entries.append(
                DirEntry(
                    name=child.name,
                    path=portable,
                    is_dir=child.is_dir(),
                    size=None if child.is_dir() else stat.st_size,
                )
            )
            if len(entries) >= limit:
                break
        return entries

    def _read_file(self, raw_path: str) -> dict[str, str]:
        target = resolve_in_jail(self._root, raw_path)
        if not target.is_file():
            raise FileNotFoundError(f"Not a file: {raw_path}")
        size = target.stat().st_size
        if size > MAX_READ_BYTES:
            raise ValueError(f"File exceeds max read size ({MAX_READ_BYTES} bytes)")

        data = target.read_bytes()
        try:
            text = data.decode("utf-8")
            return {"content": text}
        except UnicodeDecodeError:
            return {"content_b64": base64.b64encode(data).decode("ascii")}

    def _write_file(self, call: RpcCall) -> int:
        if not call.content_b64:
            raise ValueError("write_file requires content_b64")
        try:
            payload = base64.b64decode(call.content_b64, validate=True)
        except Exception as exc:
            raise ValueError("Invalid base64 content") from exc
        if len(payload) > MAX_WRITE_BYTES:
            raise ValueError(f"Content exceeds max write size ({MAX_WRITE_BYTES} bytes)")

        target = resolve_in_jail(self._root, call.path)
        if target.exists() and target.is_dir():
            raise IsADirectoryError(f"Path is a directory: {call.path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return len(payload)

    def _stat(self, raw_path: str) -> FileStat:
        rel = normalize_relative_path(raw_path)
        target = resolve_in_jail(self._root, rel)
        stat = target.stat()
        portable = rel or "."
        return FileStat(
            path=portable,
            is_dir=target.is_dir(),
            size=stat.st_size,
            mtime=stat.st_mtime,
        )

    def _mkdir(self, raw_path: str) -> FileStat:
        target = resolve_in_jail(self._root, raw_path)
        target.mkdir(parents=True, exist_ok=True)
        portable = to_portable_relative(self._root, target)
        stat = target.stat()
        return FileStat(path=portable, is_dir=True, size=0, mtime=stat.st_mtime)

    def _delete(self, raw_path: str) -> None:
        target = resolve_in_jail(self._root, raw_path)
        if target.is_dir():
            raise IsADirectoryError("delete supports files only in MVP")
        target.unlink()

    def _notify(self, call: RpcCall) -> None:
        if not self._notifications.enabled:
            return
        event_map = {
            RpcOp.LIST_DIR: ("agent_list", self._notifications.on_read),
            RpcOp.READ_FILE: ("agent_read", self._notifications.on_read),
            RpcOp.STAT: ("agent_read", self._notifications.on_read),
            RpcOp.WRITE_FILE: ("agent_write", self._notifications.on_write),
            RpcOp.MKDIR: ("agent_write", self._notifications.on_write),
            RpcOp.DELETE: ("agent_delete", self._notifications.on_delete),
        }
        mapped = event_map.get(call.op)
        if mapped is None or not mapped[1]:
            return
        logger.info("Holix Link: %s on %s", mapped[0], call.path or ".")