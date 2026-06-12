"""Daemon message handling tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from holix_link.config import ClientConfig, save_config
from holix_link.credentials import DeviceCredentials, save_credentials
from holix_link.daemon import LinkDaemon, is_daemon_running, pid_path
from holix_link.protocol import LinkPermissions, RpcOp, WsMessageType


@pytest.fixture
def paired_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLIX_LINK_HOME", str(tmp_path))
    folder = tmp_path / "workspace"
    folder.mkdir()
    (folder / "note.txt").write_text("hi\n", encoding="utf-8")
    save_config(
        ClientConfig(
            server_url="http://127.0.0.1:8000",
            gateway_ws_url="ws://127.0.0.1:8000/v1/link/ws",
            link_id="link_test",
            folder=str(folder),
        )
    )
    save_credentials(
        DeviceCredentials(
            device_public_key_b64="cHVibGlj",
            device_private_key_b64="cHJpdmF0ZQ==",
            permissions=LinkPermissions(),
        )
    )
    return tmp_path


@pytest.mark.asyncio
async def test_daemon_handles_rpc_call(paired_home) -> None:
    from holix_link.config import load_config
    from holix_link.credentials import load_credentials
    from holix_link.executor import JailExecutor
    from holix_link.paths import resolve_folder_root

    daemon = LinkDaemon()
    cfg = load_config()
    creds = load_credentials()
    assert creds is not None
    daemon._executor = JailExecutor(
        resolve_folder_root(Path(cfg.folder)),
        creds.permissions,
        cfg.notifications,
    )

    websocket = AsyncMock()
    sent: list[str] = []

    async def _send(payload: str) -> None:
        sent.append(payload)

    websocket.send = _send
    call = {
        "type": WsMessageType.RPC_CALL,
        "id": "req-1",
        "op": RpcOp.READ_FILE,
        "path": "note.txt",
    }
    await daemon._handle_message(websocket, json.dumps(call))
    assert sent
    result = json.loads(sent[0])
    assert result["ok"] is True
    assert "hi" in result["payload"]["content"]


def test_pid_helpers(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOLIX_LINK_HOME", str(tmp_path))
    assert not is_daemon_running()
    pid_path().write_text("999999999", encoding="utf-8")
    assert not is_daemon_running()