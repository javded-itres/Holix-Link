"""Holix Link background daemon — outbound WebSocket to gateway relay."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import signal
from pathlib import Path

import websockets
from websockets.asyncio.client import ClientConnection

from holix_link.config import ClientConfig, load_config
from holix_link.credentials import DeviceCredentials, load_credentials
from holix_link.executor import JailExecutor
from holix_link.paths import resolve_folder_root
from holix_link.protocol import (
    AuthMessage,
    PingMessage,
    PongMessage,
    RpcCall,
    WsMessageType,
    parse_ws_message,
)

logger = logging.getLogger(__name__)

BACKOFF_INITIAL = 1.0
BACKOFF_MAX = 60.0


def pid_path() -> Path:
    from holix_link.config import get_link_home

    return get_link_home() / "daemon.pid"


def write_pid() -> None:
    from holix_link.config import ensure_link_home

    ensure_link_home()
    pid_path().write_text(str(os.getpid()), encoding="utf-8")


def clear_pid() -> None:
    path = pid_path()
    if path.is_file():
        path.unlink()


def is_daemon_running() -> bool:
    path = pid_path()
    if not path.is_file():
        return False
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class LinkDaemon:
    def __init__(
        self,
        config: ClientConfig | None = None,
        credentials: DeviceCredentials | None = None,
    ) -> None:
        self._config = config or load_config()
        self._credentials = credentials or load_credentials()
        self._stop = asyncio.Event()
        self._executor: JailExecutor | None = None

    def validate(self) -> None:
        if not self._config.link_id:
            raise RuntimeError("Not paired. Run: holix-link pair CODE --folder PATH")
        if not self._config.gateway_ws_url:
            raise RuntimeError("gateway_ws_url missing from config — re-pair required")
        if self._credentials is None:
            raise RuntimeError("Device credentials missing — re-pair required")
        if not self._config.folder:
            raise RuntimeError("Shared folder is not configured")

    async def run(self) -> None:
        self.validate()
        assert self._credentials is not None
        root = resolve_folder_root(Path(self._config.folder))
        self._executor = JailExecutor(
            root=root,
            permissions=self._credentials.permissions,
            notifications=self._config.notifications,
        )

        write_pid()
        backoff = BACKOFF_INITIAL
        try:
            while not self._stop.is_set():
                try:
                    await self._session()
                    backoff = BACKOFF_INITIAL
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("Link daemon disconnected: %s", exc)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, BACKOFF_MAX)
        finally:
            clear_pid()

    async def _session(self) -> None:
        assert self._config.gateway_ws_url
        assert self._credentials is not None
        assert self._executor is not None

        async with websockets.connect(
            self._config.gateway_ws_url,
            open_timeout=30,
            ping_interval=30,
            ping_timeout=30,
        ) as websocket:
            auth = AuthMessage(
                link_id=self._config.link_id,
                device_public_key_b64=self._credentials.device_public_key_b64,
                nonce=secrets.token_hex(8),
            )
            await websocket.send(json.dumps(auth.model_dump()))
            raw = await websocket.recv()
            data = json.loads(raw)
            if data.get("type") != WsMessageType.AUTH_OK:
                message = data.get("message", raw)
                raise RuntimeError(f"WebSocket auth failed: {message}")

            logger.info("Holix Link connected: %s", self._config.link_id)
            async for message in websocket:
                await self._handle_message(websocket, message)

    async def _handle_message(self, websocket: ClientConnection, message: str | bytes) -> None:
        assert self._executor is not None
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        data = json.loads(message)
        msg_type = data.get("type")

        if msg_type == WsMessageType.RPC_CALL:
            call = RpcCall.model_validate(data)
            result = await self._executor.execute(call)
            await websocket.send(json.dumps(result.model_dump()))
            return

        if msg_type == WsMessageType.PING:
            ping = PingMessage.model_validate(data)
            pong = PongMessage(ts=ping.ts)
            await websocket.send(json.dumps(pong.model_dump()))
            return

        if msg_type == WsMessageType.PONG:
            return

        try:
            parse_ws_message(data)
        except ValueError:
            logger.debug("Ignoring unknown websocket message: %s", data)

    def stop(self) -> None:
        self._stop.set()


def install_signal_handlers(daemon: LinkDaemon, loop: asyncio.AbstractEventLoop) -> None:
    def _handler(*_args: object) -> None:
        daemon.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handler)
        except NotImplementedError:
            signal.signal(sig, lambda *_: _handler())


async def run_daemon(foreground: bool = True) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    daemon = LinkDaemon()
    loop = asyncio.get_running_loop()
    if foreground:
        install_signal_handlers(daemon, loop)
    await daemon.run()