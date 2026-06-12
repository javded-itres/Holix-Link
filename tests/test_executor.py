"""Jail executor RPC tests."""

from __future__ import annotations

import base64

import pytest

from holix_link.executor import JailExecutor
from holix_link.protocol import LinkPermissions, RpcCall, RpcOp


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "readme.md").write_text("# Hello\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return root


@pytest.fixture
def executor(workspace):
    return JailExecutor(workspace, LinkPermissions(read=True, write=True, mkdir=True, delete=True))


@pytest.mark.asyncio
async def test_list_dir(executor) -> None:
    result = await executor.execute(RpcCall(id="1", op=RpcOp.LIST_DIR, path="src"))
    assert result.ok is True
    assert result.payload is not None
    names = {entry.name for entry in result.payload.entries or []}
    assert names == {"main.py"}


@pytest.mark.asyncio
async def test_read_file(executor) -> None:
    result = await executor.execute(RpcCall(id="2", op=RpcOp.READ_FILE, path="readme.md"))
    assert result.ok is True
    assert result.payload is not None
    assert "Hello" in (result.payload.content or "")


@pytest.mark.asyncio
async def test_write_and_stat(executor, workspace) -> None:
    content = base64.b64encode(b"data").decode("ascii")
    write = await executor.execute(
        RpcCall(id="3", op=RpcOp.WRITE_FILE, path="out.bin", content_b64=content)
    )
    assert write.ok is True
    assert write.payload is not None
    assert write.payload.bytes_written == 4
    assert (workspace / "out.bin").read_bytes() == b"data"

    stat = await executor.execute(RpcCall(id="4", op=RpcOp.STAT, path="out.bin"))
    assert stat.ok is True
    assert stat.payload is not None
    assert stat.payload.stat is not None
    assert stat.payload.stat.size == 4


@pytest.mark.asyncio
async def test_delete_requires_permission(workspace) -> None:
    target = workspace / "readme.md"
    read_only = JailExecutor(workspace, LinkPermissions(delete=False))
    result = await read_only.execute(RpcCall(id="5", op=RpcOp.DELETE, path="readme.md"))
    assert result.ok is False
    assert "not permitted" in (result.error or "").lower()
    assert target.is_file()


@pytest.mark.asyncio
async def test_jail_escape_blocked(executor) -> None:
    result = await executor.execute(RpcCall(id="6", op=RpcOp.READ_FILE, path="../secret"))
    assert result.ok is False